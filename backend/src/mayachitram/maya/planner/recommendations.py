import uuid
from typing import Any

from mayachitram.maya.schemas import (
    CreativeRecommendation,
    Workflow,
    WorkflowTask,
)
from mayachitram.projects.models import Asset, utc_now_iso


class CreativeRecommendationService:
    """Generates grounded creative recommendations based on asset properties and platform requirements."""

    def generate_recommendations(
        self, asset: Asset | None, project_preferences: Any = None
    ) -> list[CreativeRecommendation]:
        recommendations: list[CreativeRecommendation] = []
        if not asset:
            # General recommendations when no asset is loaded
            recommendations.append(
                CreativeRecommendation(
                    id="rec_upload_hint",
                    category="workflow",
                    title="Upload High-Resolution Master Asset",
                    description="Upload your high-resolution original photo to unlock automated multi-format campaign exports.",
                    trade_offs="Larger files take slightly longer to upload but preserve maximum visual fidelity across exports.",
                    suggested_prompt="Upload a master image to start creative workflows",
                    applicable_tools=[],
                )
            )
            return recommendations

        w = asset.width
        h = asset.height
        aspect = w / h if h > 0 else 1.0

        # 1. Social Format: 1:1 Square
        if abs(aspect - 1.0) > 0.05:
            dim = min(w, h)
            left = max(0, (w - dim) // 2)
            top = max(0, (h - dim) // 2)
            recommendations.append(
                CreativeRecommendation(
                    id="rec_square_crop",
                    category="social_format",
                    title="Instagram / Feed Square (1:1)",
                    description=f"Crop centered {dim}×{dim} square optimized for Instagram and grid display.",
                    trade_offs="Trims outer edges while centering focal subject for maximum engagement in feeds.",
                    suggested_prompt=f"Make a centered 1:1 square crop ({dim}x{dim})",
                    applicable_tools=["image.crop"],
                    parameters={"left": left, "top": top, "width": dim, "height": dim},
                )
            )

        # 2. Social Format: 4:5 Portrait
        if abs(aspect - 0.8) > 0.05 and h >= 1000:
            target_w = int(h * 0.8)
            if target_w <= w:
                left = (w - target_w) // 2
                recommendations.append(
                    CreativeRecommendation(
                        id="rec_portrait_4_5",
                        category="social_format",
                        title="Instagram Portrait Post (4:5)",
                        description="Crop to 4:5 vertical aspect ratio for maximum vertical screen real estate in mobile feeds.",
                        trade_offs="Optimal mobile engagement; excludes wide peripheral background details.",
                        suggested_prompt="Crop this to 4:5 portrait ratio for Instagram",
                        applicable_tools=["image.crop"],
                        parameters={"left": left, "top": 0, "width": target_w, "height": h},
                    )
                )

        # 3. Social Format: 16:9 Landscape
        if abs(aspect - (16.0 / 9.0)) > 0.05 and w >= 800:
            target_h = int(w * 9.0 / 16.0)
            if target_h <= h:
                top = (h - target_h) // 2
                recommendations.append(
                    CreativeRecommendation(
                        id="rec_landscape_16_9",
                        category="social_format",
                        title="YouTube / Web Header (16:9)",
                        description="Crop to 16:9 widescreen format suitable for YouTube thumbnails, web hero banners, and presentation slides.",
                        trade_offs="Horizontal composition trims vertical elements from the top and bottom.",
                        suggested_prompt="Crop this into 16:9 landscape format",
                        applicable_tools=["image.crop"],
                        parameters={"left": 0, "top": top, "width": w, "height": target_h},
                    )
                )

        # 4. Format & Compression: Modern WebP Delivery
        if "webp" not in asset.media_type.lower():
            recommendations.append(
                CreativeRecommendation(
                    id="rec_webp_conversion",
                    category="performance",
                    title="Convert to WebP (Optimized Web Delivery)",
                    description="Convert image to modern WebP format with 85% quality to reduce file size by 30-50% with zero perceptible loss.",
                    trade_offs="Significantly faster page load times; supported by >97% of modern web browsers.",
                    suggested_prompt="Convert this asset to WebP with 85% quality",
                    applicable_tools=["image.convert_format"],
                    parameters={"target_format": "WEBP", "quality": 85},
                )
            )

        # 5. Visual Enhancement: Vibrant Studio Grade
        recommendations.append(
            CreativeRecommendation(
                id="rec_vibrant_grade",
                category="color_treatment",
                title="Vibrant Commercial Color Grade",
                description="Apply a subtle +15% saturation boost, +10% contrast enhancement, and slight warmth (+10) for commercial punch.",
                trade_offs="Enhances color pop and visual appetite; might slightly warm neutral skin tones.",
                suggested_prompt="Apply vibrant commercial contrast and saturation enhancement",
                applicable_tools=[
                    "image.adjust_contrast",
                    "image.adjust_saturation",
                    "image.adjust_temperature",
                ],
                parameters={"contrast": 1.10, "saturation": 1.15, "temperature": 10},
            )
        )

        # 6. Dramatic Monochrome Treatment
        recommendations.append(
            CreativeRecommendation(
                id="rec_monochrome_grade",
                category="color_treatment",
                title="High-Contrast Dramatic Black & White",
                description="Desaturate completely (grayscale) and increase contrast to 1.3x for architectural or fine-art impact.",
                trade_offs="Removes all color information in favor of texture, light, and silhouette.",
                suggested_prompt="Convert to high-contrast black and white",
                applicable_tools=["image.adjust_saturation", "image.adjust_contrast"],
                parameters={"saturation": 0.0, "contrast": 1.30},
            )
        )

        return recommendations

    def build_workflow_from_recommendation(
        self,
        recommendation: CreativeRecommendation,
        project_id: str,
        asset: Asset,
    ) -> Workflow:
        now = utc_now_iso()
        tasks: list[WorkflowTask] = []
        rec_id = recommendation.id

        if rec_id == "rec_square_crop":
            tasks.append(
                WorkflowTask(
                    task_id="task_1",
                    tool_name="image.crop",
                    description=f"Crop centered square ({recommendation.parameters['width']}x{recommendation.parameters['height']})",
                    parameters=recommendation.parameters,
                    input_asset_id=asset.id,
                )
            )
        elif rec_id == "rec_portrait_4_5":
            tasks.append(
                WorkflowTask(
                    task_id="task_1",
                    tool_name="image.crop",
                    description=f"Crop 4:5 portrait ({recommendation.parameters['width']}x{recommendation.parameters['height']})",
                    parameters=recommendation.parameters,
                    input_asset_id=asset.id,
                )
            )
        elif rec_id == "rec_landscape_16_9":
            tasks.append(
                WorkflowTask(
                    task_id="task_1",
                    tool_name="image.crop",
                    description=f"Crop 16:9 widescreen ({recommendation.parameters['width']}x{recommendation.parameters['height']})",
                    parameters=recommendation.parameters,
                    input_asset_id=asset.id,
                )
            )
        elif rec_id == "rec_webp_conversion":
            tasks.append(
                WorkflowTask(
                    task_id="task_1",
                    tool_name="image.convert_format",
                    description="Convert to WebP with 85% compression quality",
                    parameters=recommendation.parameters,
                    input_asset_id=asset.id,
                )
            )
        elif rec_id == "rec_vibrant_grade":
            tasks.append(
                WorkflowTask(
                    task_id="task_1",
                    tool_name="image.adjust_contrast",
                    description="Boost image contrast by 10%",
                    parameters={"factor": 1.10},
                    input_asset_id=asset.id,
                )
            )
            tasks.append(
                WorkflowTask(
                    task_id="task_2",
                    tool_name="image.adjust_saturation",
                    description="Boost color saturation by 15%",
                    parameters={"factor": 1.15},
                    dependencies=["task_1"],
                )
            )
            tasks.append(
                WorkflowTask(
                    task_id="task_3",
                    tool_name="image.adjust_temperature",
                    description="Warm color temperature (+10)",
                    parameters={"shift": 10},
                    dependencies=["task_2"],
                )
            )
        elif rec_id == "rec_monochrome_grade":
            tasks.append(
                WorkflowTask(
                    task_id="task_1",
                    tool_name="image.adjust_saturation",
                    description="Desaturate image to grayscale",
                    parameters={"factor": 0.0},
                    input_asset_id=asset.id,
                )
            )
            tasks.append(
                WorkflowTask(
                    task_id="task_2",
                    tool_name="image.adjust_contrast",
                    description="Boost monochrome contrast by 30%",
                    parameters={"factor": 1.30},
                    dependencies=["task_1"],
                )
            )

        return Workflow(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=recommendation.title,
            description=recommendation.description,
            tasks=tasks,
            status="draft",
            execution_mode="execute",
            created_at=now,
            updated_at=now,
        )
