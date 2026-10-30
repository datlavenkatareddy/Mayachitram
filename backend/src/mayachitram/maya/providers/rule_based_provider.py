import json
import re
from typing import Any

from mayachitram.maya.providers.base import BaseModelProvider, ModelCapability


class RuleBasedSemanticProvider(BaseModelProvider):
    """
    Local, deterministic semantic provider.
    Parses creative user intentions, formats, and adjustments when remote AI APIs are offline or unconfigured.
    """

    @property
    def provider_id(self) -> str:
        return "local_rule_based"

    @property
    def model_name(self) -> str:
        return "mayachitram-semantic-rules-v1"

    def get_capabilities(self) -> list[ModelCapability]:
        return [ModelCapability.TEXT_GENERATION, ModelCapability.STRUCTURED_OUTPUT]

    async def generate_response(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.2,
    ) -> str:
        last_user_msg = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                last_user_msg = m.get("content", "")
                break

        if json_mode:
            return self._parse_to_json_plan(last_user_msg)
        return self._generate_conversational_reply(last_user_msg)

    def _generate_conversational_reply(self, prompt: str) -> str:
        p = prompt.lower().strip()
        if re.search(r"\b(hello|hi|hey|greetings)\b", p):
            return (
                "Hello! I am Maya, your AI creative assistant for MayaChitram. "
                "I can plan and execute verified editing workflows on your assets—such as cropping for social media, "
                "color grading, format conversion, and multi-format campaign exports. How can I help you today?"
            )
        if re.search(r"\b(help|what can you do|features)\b", p):
            return (
                "Here is what I can do:\n"
                "• **Social Formats:** Square 1:1, Instagram Portrait 4:5, Landscape 16:9 crops.\n"
                "• **Adjustments:** Brightness, contrast, saturation, and color temperature tuning.\n"
                "• **Transformations:** Rotate (90°, 180°, 270°), flip horizontal and vertical.\n"
                "• **Format & Quality:** Convert to WebP, JPEG, PNG, or compress for web delivery.\n"
                "• **Multi-step Campaigns:** Chain operations into a reproducible workflow with preview."
            )
        if any(w in p for w in ["suggest", "recommend", "idea", "tips", "advice", "what should", "how should"]):
            return (
                "Here are my creative suggestions for your active project asset:\n\n"
                "• **Aspect Ratio Optimization**: If publishing to Instagram or mobile feeds, crop to **1:1 Square** or **4:5 Vertical Portrait** to maximize viewport real estate.\n"
                "• **Delivery & Web Performance**: Convert to **WebP (quality 85)** to reduce asset file size by 30–50% without noticeable compression artifacts.\n"
                "• **Visual Punch**: If the image looks flat, boost contrast by 10–15% or warm up the color temperature to 6200K for richer skin tones and lighting.\n\n"
                "Check out the interactive recommendation cards below to preview and apply any of these approaches with one click!"
            )
        return (
            f"I have reviewed your request: '{prompt}'. "
            "I can generate a verified execution plan for your active project asset. "
            "Please review the proposed plan below and confirm to proceed."
        )

    def _parse_to_json_plan(self, prompt: str) -> str:
        p = prompt.lower().strip()
        steps: list[dict[str, Any]] = []
        summary = "Creative transformation plan"

        # 1. Square Crop
        if "square" in p or "1:1" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.crop",
                    "parameters": {"left": 0, "top": 0, "width": 1080, "height": 1080},
                    "rationale": "Crop image into a centered 1:1 square.",
                }
            )
            summary = "Crop asset into a 1:1 square."

        # 2. Portrait 4:5 Crop
        elif "4:5" in p or "portrait" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.crop",
                    "parameters": {"left": 0, "top": 0, "width": 1080, "height": 1350},
                    "rationale": "Crop image to 4:5 vertical portrait aspect ratio for mobile feeds.",
                }
            )
            summary = "Crop asset to 4:5 portrait ratio."

        # 3. Landscape 16:9
        elif "16:9" in p or "landscape" in p or "youtube" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.crop",
                    "parameters": {"left": 0, "top": 0, "width": 1920, "height": 1080},
                    "rationale": "Crop to 16:9 widescreen format.",
                }
            )
            summary = "Crop asset to 16:9 widescreen format."

        # 4. Rotation
        if "rotate" in p:
            deg = 90.0
            if "180" in p:
                deg = 180.0
            elif "270" in p or "counter" in p:
                deg = 270.0
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.rotate",
                    "parameters": {"degrees": deg, "expand": True},
                    "rationale": f"Rotate image {deg} degrees clockwise.",
                }
            )
            summary = f"Rotate image {deg}°."

        # 5. Flip
        if "flip" in p:
            h = "horiz" in p or "left" in p or "right" in p or ("vert" not in p)
            v = "vert" in p or "up" in p or "down" in p
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.flip",
                    "parameters": {"horizontal": h, "vertical": v},
                    "rationale": "Flip image orientation.",
                }
            )

        # 6. Adjustments
        if "bright" in p or "dark" in p:
            factor = 1.2 if "bright" in p else 0.8
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.adjust_brightness",
                    "parameters": {"factor": factor},
                    "rationale": "Tune image brightness.",
                }
            )

        if "contrast" in p:
            factor = 1.25 if "high" in p or "boost" in p or "more" in p else 0.85
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.adjust_contrast",
                    "parameters": {"factor": factor},
                    "rationale": "Enhance visual contrast.",
                }
            )

        if "black and white" in p or "monochrome" in p or "grayscale" in p or "desaturat" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.adjust_saturation",
                    "parameters": {"factor": 0.0},
                    "rationale": "Convert to black and white.",
                }
            )
        elif "saturat" in p or "vibrant" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.adjust_saturation",
                    "parameters": {"factor": 1.3},
                    "rationale": "Boost color saturation.",
                }
            )

        if "warm" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.adjust_temperature",
                    "parameters": {"shift": 25},
                    "rationale": "Warm color temperature.",
                }
            )
        elif "cool" in p or "blue" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.adjust_temperature",
                    "parameters": {"shift": -25},
                    "rationale": "Cool color temperature.",
                }
            )

        # 7. Format conversion
        if "webp" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.convert_format",
                    "parameters": {"target_format": "WEBP", "quality": 85},
                    "rationale": "Convert to WebP format.",
                }
            )
        elif "jpeg" in p or "jpg" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.convert_format",
                    "parameters": {"target_format": "JPEG", "quality": 90},
                    "rationale": "Convert to JPEG format.",
                }
            )
        elif "png" in p:
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.convert_format",
                    "parameters": {"target_format": "PNG"},
                    "rationale": "Convert to PNG format.",
                }
            )

        # 8. Resize dimensions
        match = re.search(r"(\d{2,4})\s*[x×]\s*(\d{2,4})", p)
        if match:
            w_val, h_val = int(match.group(1)), int(match.group(2))
            steps.append(
                {
                    "step_id": len(steps) + 1,
                    "tool_name": "image.resize",
                    "parameters": {"width": w_val, "height": h_val, "preserve_aspect": False},
                    "rationale": f"Resize to {w_val}x{h_val}px.",
                }
            )
            summary = f"Resize asset to {w_val}×{h_val}."

        if not steps:
            # Fallback advice if no matching creative operation pattern found
            return json.dumps(
                {
                    "summary": "Could not identify specific creative operation.",
                    "steps": [],
                    "missing_information": "Please specify an editing action, such as 'crop to square', 'rotate 90 degrees', 'adjust brightness', or 'convert to webp'.",
                }
            )

        return json.dumps({"summary": summary, "steps": steps, "missing_information": None})
