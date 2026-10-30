import json
import logging
import re
import uuid

from groq import AsyncGroq
from pydantic import ValidationError

from mayachitram.core.config import Settings
from mayachitram.maya.planner.recommendations import CreativeRecommendationService
from mayachitram.maya.providers.router import ProviderRouter
from mayachitram.maya.registry.tools import ToolRegistry
from mayachitram.maya.repository import MayaRepository
from mayachitram.maya.schemas import (
    ConversationMessage,
    ExecutionMode,
    PlannedStep,
    PlanResponse,
    SendMessageRequest,
    SendMessageResponse,
    Workflow,
    WorkflowTask,
)
from mayachitram.projects.models import Asset, utc_now_iso
from mayachitram.projects.service import ProjectService

logger = logging.getLogger(__name__)


class MayaPlanner:
    """Natural-language AI planner translating user intentions into verified creative tool plans and workflows."""

    def __init__(
        self,
        settings: Settings,
        tool_registry: ToolRegistry,
        project_service: ProjectService,
        maya_repository: MayaRepository | None = None,
    ) -> None:
        self.settings = settings
        self.tool_registry = tool_registry
        self.project_service = project_service
        self.maya_repository = maya_repository
        self.recommendations_service = CreativeRecommendationService()
        self.router = ProviderRouter(settings)

        # Retain direct _groq_client for backward compatibility with mock tests
        self._groq_client: AsyncGroq | None = None
        if settings.groq_api_key:
            self._groq_client = AsyncGroq(
                api_key=settings.groq_api_key,
                timeout=settings.groq_timeout_seconds,
            )

    async def plan(
        self,
        project_id: str,
        user_prompt: str,
        target_asset_id: str | None = None,
    ) -> PlanResponse:
        """Create a structured linear plan for backward-compatible execution."""
        self.project_service.get_project(project_id)
        assets = self.project_service.list_assets(project_id, limit=20)

        # Resolve target asset
        target_asset: Asset | None = None
        if target_asset_id:
            try:
                target_asset = self.project_service.get_asset(target_asset_id)
            except Exception:
                target_asset = None
        if not target_asset and assets:
            target_asset = assets[0]

        # Attempt AI planning if Groq is available
        plan: PlanResponse | None = None
        if self._groq_client:
            try:
                plan = await self._plan_with_groq(
                    project_id=project_id,
                    assets=assets,
                    target_asset=target_asset,
                    user_prompt=user_prompt,
                )
            except Exception as exc:
                logger.warning("Groq planner failed, using deterministic fallback: %s", exc)
                plan = None

        # Fallback to deterministic semantic parser if Groq unavailable or failed
        if plan is None:
            plan = self._fallback_plan(
                project_id=project_id,
                target_asset=target_asset,
                user_prompt=user_prompt,
            )

        # Validate each proposed step against tool registry schemas
        validated_steps: list[PlannedStep] = []
        can_execute = True
        missing_info = plan.missing_information

        for step in plan.steps:
            tool = self.tool_registry.get(step.tool_name)
            if not tool:
                can_execute = False
                missing_info = f"Requested tool '{step.tool_name}' is not supported."
                continue
            try:
                validated_params = tool.params_class.model_validate(step.parameters)
                validated_steps.append(
                    PlannedStep(
                        step_id=step.step_id,
                        tool_name=step.tool_name,
                        parameters=validated_params.model_dump(),
                        rationale=step.rationale,
                        input_asset_id=step.input_asset_id,
                        requires_confirmation=tool.is_destructive or tool.requires_approval,
                        dependencies=step.dependencies,
                        is_branch=step.is_branch,
                    )
                )
            except ValidationError as exc:
                can_execute = False
                missing_info = f"Constraint violation for {step.tool_name}: {exc.errors()[0]['msg']}"

        return PlanResponse(
            project_id=project_id,
            target_asset_id=target_asset.id if target_asset else None,
            user_prompt=user_prompt,
            summary=plan.summary,
            steps=validated_steps,
            missing_information=missing_info,
            can_execute=can_execute and len(validated_steps) > 0,
        )

    async def plan_workflow(
        self,
        project_id: str,
        user_prompt: str,
        target_asset_id: str | None = None,
        execution_mode: ExecutionMode = "execute",
    ) -> Workflow:
        """Create a durable DAG workflow with dependencies and validation."""
        plan_res = await self.plan(
            project_id=project_id,
            user_prompt=user_prompt,
            target_asset_id=target_asset_id,
        )

        tasks: list[WorkflowTask] = []
        for idx, step in enumerate(plan_res.steps, start=1):
            task_id = f"task_{idx}"
            deps = [f"task_{dep_id}" for dep_id in step.dependencies] if step.dependencies else []
            # Chain sequentially if no explicit dependencies given and not multi-deliverable branch
            if not deps and idx > 1 and not getattr(step, "is_branch", False):
                deps = [f"task_{idx - 1}"]

            tasks.append(
                WorkflowTask(
                    task_id=task_id,
                    tool_name=step.tool_name,
                    description=step.rationale or f"Execute {step.tool_name}",
                    parameters=step.parameters,
                    dependencies=deps,
                    status="pending",
                    input_asset_id=step.input_asset_id or target_asset_id,
                    requires_approval=step.requires_confirmation,
                )
            )

        if self.maya_repository:
            workflow = self.maya_repository.create_workflow(
                project_id=project_id,
                title=plan_res.summary,
                description=f"Generated from: '{user_prompt}'",
                tasks=tasks,
                execution_mode=execution_mode,
            )
        else:
            now = utc_now_iso()
            workflow = Workflow(
                id=str(uuid.uuid4()),
                project_id=project_id,
                title=plan_res.summary,
                description=f"Generated from: '{user_prompt}'",
                tasks=tasks,
                status="draft",
                execution_mode=execution_mode,
                created_at=now,
                updated_at=now,
            )
        return workflow

    async def handle_chat_message(self, req: SendMessageRequest) -> SendMessageResponse:
        """Process conversational multi-turn messages, planning workflows or answering queries."""
        project_id = req.project_id
        self.project_service.get_project(project_id)
        assets = self.project_service.list_assets(project_id, limit=20)
        msg_lower = req.message.lower().strip()

        # 1. Resolve active asset & handle ambiguous asset references
        target_asset: Asset | None = None
        if req.target_asset_id:
            try:
                target_asset = self.project_service.get_asset(req.target_asset_id)
            except Exception:
                target_asset = None

        if not target_asset and assets:
            # Check for ordinal reference like "second image"
            if "second" in msg_lower or "2nd" in msg_lower:
                if len(assets) >= 2:
                    target_asset = assets[1]
            elif "third" in msg_lower or "3rd" in msg_lower:
                if len(assets) >= 3:
                    target_asset = assets[2]
            else:
                target_asset = assets[0]

        # 2. Ambiguity check: if user says "the other image" and multiple plausible assets exist
        if "the other image" in msg_lower and len(assets) > 2:
            clarify_text = (
                f"There are multiple assets in this project ({', '.join([a.original_filename for a in assets])}). "
                "Which specific asset would you like to edit?"
            )
            return self._build_clarification_response(req, clarify_text, target_asset)

        # 3. Check for unsupported capabilities (3D, background removal, audio, voiceover)
        unsupported_keywords = [
            "3d", "mesh", "cutout", "remove background", "bg removal",
            "voiceover", "audio", "generate video from scratch", "text to video"
        ]
        if any(uk in msg_lower for uk in unsupported_keywords):
            clarify_text = (
                "That operation (e.g. 3D modeling or background removal) is currently not supported in Mayachitram v1. "
                "Supported tools include: image crop (1:1, 4:5, 16:9), resize, rotate, flip, format conversion (JPEG/PNG/WebP), "
                "compression, brightness, contrast, saturation, and color temperature."
            )
            return self._build_clarification_response(req, clarify_text, target_asset)

        # 4. Check for creative request intent vs advisory/suggestion query
        creative_keywords = [
            "crop", "square", "portrait", "landscape", "resize", "rotate", "flip",
            "convert", "webp", "jpeg", "png", "bright", "dark", "contrast", "saturat",
            "monochrome", "black and white", "warm", "cool", "temperature", "campaign"
        ]
        is_creative_request = any(k in msg_lower for k in creative_keywords)

        is_advisory_request = (
            any(
                phrase in msg_lower
                for phrase in [
                    "suggest", "recommend", "advice", "what do you think",
                    "what should", "how should", "tips", "ideas", "opinion",
                ]
            )
            or (req.execution_mode == "assist" and not any(w in msg_lower for w in ["execute", "apply now", "run this"]))
        )

        # 5. Check missing asset when creative operation is requested
        if is_creative_request and not is_advisory_request and not target_asset and not assets:
            clarify_text = (
                "To perform image transformations, please upload or select an image asset in the project first. "
                "Once an asset is loaded, I can inspect its resolution and build an execution pipeline."
            )
            return self._build_clarification_response(req, clarify_text, None)

        # 6. Check cross-engine requests combining Image, Design, and Video
        has_design_req = any(w in msg_lower for w in ["design", "canvas", "graphic"])
        has_video_req = any(w in msg_lower for w in ["video", "clip", "teaser", "promo video"])

        if has_design_req or has_video_req:
            if not is_creative_request:
                clarify_text = (
                    "Design Engine and Video Engine operations are currently being developed in parallel by the collaborator. "
                    "Their adapters are defined and will become executable once their engine services are connected. "
                    "In the meantime, all 10 Image Engine tools are fully operational."
                )
                return self._build_clarification_response(req, clarify_text, target_asset)

        # 7. Conversational greeting, advice, or suggestions (chatbot mode)
        if not is_creative_request or is_advisory_request:
            messages = [{"role": "user", "content": req.message}]
            reply, _ = await self.router.generate_response(
                messages=messages,
                system_prompt="You are Maya, the expert AI Creative Assistant for MayaChitram. Provide helpful creative advice, suggestions, and trade-offs.",
                json_mode=False,
            )
            return self._build_text_response(req, reply, target_asset)

        # 8. Create Plan and Workflow
        plan_res = await self.plan(
            project_id=project_id,
            user_prompt=req.message,
            target_asset_id=target_asset.id if target_asset else None,
        )

        # If constraint violation or cannot execute
        if not plan_res.can_execute:
            reason = plan_res.missing_information or "The requested operation violates tool parameter constraints."
            clarify_text = f"I could not build an executable plan: {reason}"
            return self._build_clarification_response(req, clarify_text, target_asset)

        workflow = await self.plan_workflow(
            project_id=project_id,
            user_prompt=req.message,
            target_asset_id=target_asset.id if target_asset else None,
            execution_mode=req.execution_mode,
        )

        step_count = len(workflow.tasks)
        assistant_content = (
            f"I have created a {step_count}-step creative workflow: **{workflow.title}**.\n"
            "Review the dependency pipeline below and click **Approve & Execute Workflow** to run."
        )

        if has_design_req or has_video_req:
            assistant_content += (
                "\n\n*(Note: Design and Video operations were identified and will be linked once the collaborator's "
                "Design and Video engines are connected.)*"
            )

        return self._build_workflow_response(req, assistant_content, workflow, target_asset)

    def _build_clarification_response(
        self, req: SendMessageRequest, content: str, target_asset: Asset | None
    ) -> SendMessageResponse:
        recommendations = self.recommendations_service.generate_recommendations(target_asset)
        if self.maya_repository:
            session = self.maya_repository.get_or_create_conversation(
                project_id=req.project_id, conversation_id=req.conversation_id
            )
            conv_id = session.id
            user_msg = self.maya_repository.add_message(conv_id, "user", req.message)
            assistant_msg = self.maya_repository.add_message(
                conv_id, "assistant", content, message_type="clarification"
            )
        else:
            conv_id = req.conversation_id or str(uuid.uuid4())
            now = utc_now_iso()
            user_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role="user",
                content=req.message,
                message_type="text",
                created_at=now,
            )
            assistant_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role="assistant",
                content=content,
                message_type="clarification",
                created_at=now,
            )
        return SendMessageResponse(
            conversation_id=conv_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            workflow=None,
            recommendations=recommendations,
        )

    def _build_text_response(
        self, req: SendMessageRequest, content: str, target_asset: Asset | None
    ) -> SendMessageResponse:
        recommendations = self.recommendations_service.generate_recommendations(target_asset)
        if self.maya_repository:
            session = self.maya_repository.get_or_create_conversation(
                project_id=req.project_id, conversation_id=req.conversation_id
            )
            conv_id = session.id
            user_msg = self.maya_repository.add_message(conv_id, "user", req.message)
            assistant_msg = self.maya_repository.add_message(
                conv_id, "assistant", content, message_type="text"
            )
        else:
            conv_id = req.conversation_id or str(uuid.uuid4())
            now = utc_now_iso()
            user_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role="user",
                content=req.message,
                message_type="text",
                created_at=now,
            )
            assistant_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role="assistant",
                content=content,
                message_type="text",
                created_at=now,
            )
        return SendMessageResponse(
            conversation_id=conv_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            workflow=None,
            recommendations=recommendations,
        )

    def _build_workflow_response(
        self,
        req: SendMessageRequest,
        content: str,
        workflow: Workflow,
        target_asset: Asset | None,
    ) -> SendMessageResponse:
        recommendations = self.recommendations_service.generate_recommendations(target_asset)
        if self.maya_repository:
            session = self.maya_repository.get_or_create_conversation(
                project_id=req.project_id, conversation_id=req.conversation_id
            )
            conv_id = session.id
            user_msg = self.maya_repository.add_message(conv_id, "user", req.message)
            assistant_msg = self.maya_repository.add_message(
                conv_id,
                "assistant",
                content,
                message_type="workflow",
                metadata={"workflow_id": workflow.id},
            )
        else:
            conv_id = req.conversation_id or str(uuid.uuid4())
            now = utc_now_iso()
            user_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role="user",
                content=req.message,
                message_type="text",
                created_at=now,
            )
            assistant_msg = ConversationMessage(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                role="assistant",
                content=content,
                message_type="workflow",
                metadata={"workflow_id": workflow.id},
                created_at=now,
            )
        return SendMessageResponse(
            conversation_id=conv_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            workflow=workflow,
            recommendations=recommendations,
        )

    async def _plan_with_groq(
        self,
        project_id: str,
        assets: list[Asset],
        target_asset: Asset | None,
        user_prompt: str,
    ) -> PlanResponse | None:
        assert self._groq_client is not None

        tools_context = [
            {
                "tool_name": tool.name,
                "description": tool.description,
                "parameters_schema": tool.params_class.model_json_schema(),
            }
            for tool in self.tool_registry._tools.values()
        ]

        asset_info = None
        if target_asset:
            asset_info = {
                "id": target_asset.id,
                "filename": target_asset.original_filename,
                "width": target_asset.width,
                "height": target_asset.height,
                "media_type": target_asset.media_type,
            }

        system_prompt = (
            "You are Maya, the expert AI Creative Assistant for MayaChitram.\n"
            "Your job is to translate the user's natural language creative request into a verified sequence of tool calls.\n"
            "Rules:\n"
            "1. ONLY use tools from the provided available tools list.\n"
            "2. Tool parameters must strictly match the parameter schemas.\n"
            "3. If the user refers to 'this image', 'the photo', or gives editing instructions, use the current active asset's dimensions.\n"
            "4. For square crops: calculate centered crop (left = (width - min_dim)//2, top = (height - min_dim)//2, width = min_dim, height = min_dim).\n"
            "5. Return ONLY a JSON object with keys:\n"
            "   - 'summary': concise description of what the plan does\n"
            "   - 'steps': array of objects { 'step_id': 1, 'tool_name': '...', 'parameters': { ... }, 'rationale': '...', 'dependencies': [] }\n"
            "   - 'missing_information': null or string if the request cannot be fulfilled."
        )

        user_content = json.dumps(
            {
                "project_id": project_id,
                "active_asset": asset_info,
                "available_tools": tools_context,
                "user_request": user_prompt,
            }
        )

        response = await self._groq_client.chat.completions.create(
            model=self.settings.groq_chat_model,
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        content = response.choices[0].message.content or "{}"
        data = json.loads(content)

        summary = data.get("summary", "Creative operation plan")
        raw_steps = data.get("steps", [])
        missing_info = data.get("missing_information")

        steps: list[PlannedStep] = []
        for idx, s in enumerate(raw_steps, start=1):
            steps.append(
                PlannedStep(
                    step_id=idx,
                    tool_name=s.get("tool_name", ""),
                    parameters=s.get("parameters", {}),
                    rationale=s.get("rationale", ""),
                    input_asset_id=s.get("input_asset_id")
                    or (target_asset.id if idx == 1 and target_asset else None),
                    dependencies=s.get("dependencies", []),
                )
            )

        return PlanResponse(
            project_id=project_id,
            target_asset_id=target_asset.id if target_asset else None,
            user_prompt=user_prompt,
            summary=summary,
            steps=steps,
            missing_information=missing_info,
        )

    def _fallback_plan(
        self,
        project_id: str,
        target_asset: Asset | None,
        user_prompt: str,
    ) -> PlanResponse:
        prompt_lower = user_prompt.lower().strip()
        steps: list[PlannedStep] = []
        summary = "Applied matching image transformation."
        missing_info: str | None = None

        width = target_asset.width if target_asset else 1000
        height = target_asset.height if target_asset else 1000

        # Scenario A: Check for multiple deliverable requests (branching DAG)
        is_multi_deliverable = any(
            phrase in prompt_lower
            for phrase in ["deliverables", "versions", "campaign formats", "all formats", "square and landscape"]
        )

        if is_multi_deliverable:
            # Task 1: 1:1 Square
            dim = min(width, height)
            left_sq = max(0, (width - dim) // 2)
            top_sq = max(0, (height - dim) // 2)
            steps.append(
                PlannedStep(
                    step_id=1,
                    tool_name="image.crop",
                    parameters={"left": left_sq, "top": top_sq, "width": dim, "height": dim},
                    rationale="1:1 Square deliverable for feed posts",
                    input_asset_id=target_asset.id if target_asset else None,
                    is_branch=True,
                )
            )
            # Task 2: 4:5 Portrait
            target_w = int(height * 0.8)
            if target_w <= width:
                left_pt = (width - target_w) // 2
                top_pt = 0
                crop_pt_w = target_w
                crop_pt_h = height
            else:
                crop_pt_w = width
                crop_pt_h = int(width / 0.8)
                left_pt = 0
                top_pt = max(0, (height - crop_pt_h) // 2)
            steps.append(
                PlannedStep(
                    step_id=2,
                    tool_name="image.crop",
                    parameters={"left": left_pt, "top": top_pt, "width": crop_pt_w, "height": crop_pt_h},
                    rationale="4:5 Portrait deliverable for mobile feeds",
                    input_asset_id=target_asset.id if target_asset else None,
                    is_branch=True,
                )
            )
            # Task 3: 16:9 Landscape
            target_h = int(width * 9.0 / 16.0)
            if target_h <= height:
                top_ls = (height - target_h) // 2
                left_ls = 0
                crop_ls_w = width
                crop_ls_h = target_h
            else:
                crop_ls_h = height
                crop_ls_w = int(height * 16.0 / 9.0)
                left_ls = max(0, (width - crop_ls_w) // 2)
                top_ls = 0
            steps.append(
                PlannedStep(
                    step_id=len(steps) + 1,
                    tool_name="image.crop",
                    parameters={"left": left_ls, "top": top_ls, "width": crop_ls_w, "height": crop_ls_h},
                    rationale="16:9 Landscape deliverable for web/presentation",
                    input_asset_id=target_asset.id if target_asset else None,
                    is_branch=True,
                )
            )
            summary = f"Generated {len(steps)} multi-format campaign deliverables."
            return PlanResponse(
                project_id=project_id,
                target_asset_id=target_asset.id if target_asset else None,
                user_prompt=user_prompt,
                summary=summary,
                steps=steps,
                can_execute=True,
            )

        # Scenario B: Ordered sequential transformations pipeline
        prev_step_id: int | None = None

        # 1. Crop operations (square, portrait, landscape, or generic crop)
        if "square" in prompt_lower or "1:1" in prompt_lower or (
            "crop" in prompt_lower
            and not any(x in prompt_lower for x in ["portrait", "4:5", "landscape", "16:9"])
        ):
            dim = min(width, height)
            left = max(0, (width - dim) // 2)
            top = max(0, (height - dim) // 2)
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.crop",
                    parameters={"left": left, "top": top, "width": dim, "height": dim},
                    rationale="Centered square crop",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        elif "portrait" in prompt_lower or "4:5" in prompt_lower:
            target_w = int(height * 0.8)
            if target_w <= width:
                left = (width - target_w) // 2
                top = 0
                c_w = target_w
                c_h = height
            else:
                c_w = width
                c_h = int(width / 0.8)
                left = 0
                top = max(0, (height - c_h) // 2)
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.crop",
                    parameters={"left": left, "top": top, "width": c_w, "height": c_h},
                    rationale="Crop to 4:5 vertical portrait for mobile feeds",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        elif "landscape" in prompt_lower or "16:9" in prompt_lower:
            target_h = int(width * 9.0 / 16.0)
            if target_h <= height:
                top = (height - target_h) // 2
                left = 0
                c_w = width
                c_h = target_h
            else:
                c_h = height
                c_w = int(height * 16.0 / 9.0)
                left = max(0, (width - c_w) // 2)
                top = 0
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.crop",
                    parameters={"left": left, "top": top, "width": c_w, "height": c_h},
                    rationale="Crop to 16:9 landscape aspect ratio",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        # 2. Rotation & Flip
        if "rotate" in prompt_lower:
            deg = 90.0
            if "180" in prompt_lower:
                deg = 180.0
            elif "270" in prompt_lower or "counter" in prompt_lower:
                deg = 270.0
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.rotate",
                    parameters={"degrees": deg, "expand": True},
                    rationale=f"Rotate {deg} degrees clockwise",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        if "flip" in prompt_lower:
            h_flip = "horizontal" in prompt_lower or "left" in prompt_lower or "right" in prompt_lower or ("vertical" not in prompt_lower)
            v_flip = "vertical" in prompt_lower or "up" in prompt_lower or "down" in prompt_lower
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.flip",
                    parameters={"horizontal": h_flip, "vertical": v_flip},
                    rationale="Flip image orientation",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        # 3. Tone & Color Adjustments
        if "bright" in prompt_lower or "dark" in prompt_lower:
            factor = 1.25 if "bright" in prompt_lower else 0.8
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.adjust_brightness",
                    parameters={"factor": factor},
                    rationale="Adjust brightness",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        if "contrast" in prompt_lower:
            factor = 1.30 if "high" in prompt_lower or "boost" in prompt_lower else 0.85
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.adjust_contrast",
                    parameters={"factor": factor},
                    rationale="Adjust contrast",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        if "black and white" in prompt_lower or "monochrome" in prompt_lower or "grayscale" in prompt_lower:
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.adjust_saturation",
                    parameters={"factor": 0.0},
                    rationale="Convert to black and white",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id
        elif "saturation" in prompt_lower or "vibrant" in prompt_lower:
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.adjust_saturation",
                    parameters={"factor": 1.35},
                    rationale="Boost color saturation",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        if "warm" in prompt_lower:
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.adjust_temperature",
                    parameters={"shift": 25},
                    rationale="Warm color temperature",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id
        elif "cool" in prompt_lower or "blue" in prompt_lower:
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.adjust_temperature",
                    parameters={"shift": -25},
                    rationale="Cool color temperature",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        # 4. Format Conversion
        if "webp" in prompt_lower:
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.convert_format",
                    parameters={"target_format": "WEBP", "quality": 85},
                    rationale="Convert to WebP format",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id
        elif "jpeg" in prompt_lower or "jpg" in prompt_lower:
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.convert_format",
                    parameters={"target_format": "JPEG", "quality": 90},
                    rationale="Convert to JPEG format",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )
            prev_step_id = step_id

        # 5. Dimensions: e.g. 800x600 or 1080x1350
        dim_match = re.search(r"(\d{2,6})\s*[x×]\s*(\d{2,6})", prompt_lower)
        if dim_match:
            w_val = int(dim_match.group(1))
            h_val = int(dim_match.group(2))
            step_id = len(steps) + 1
            steps.append(
                PlannedStep(
                    step_id=step_id,
                    tool_name="image.resize",
                    parameters={"width": w_val, "height": h_val, "preserve_aspect": False},
                    rationale=f"Resize to {w_val}x{h_val}",
                    dependencies=[prev_step_id] if prev_step_id else [],
                )
            )

        if not steps:
            missing_info = (
                "Could not infer specific tool parameters from request. "
                "Please try 'crop 1:1 square', 'rotate 90', or 'convert to webp'."
            )
        else:
            summary = f"Pipeline of {len(steps)} creative operation(s)."

        return PlanResponse(
            project_id=project_id,
            target_asset_id=target_asset.id if target_asset else None,
            user_prompt=user_prompt,
            summary=summary,
            steps=steps,
            missing_information=missing_info,
            can_execute=len(steps) > 0 and missing_info is None,
        )
