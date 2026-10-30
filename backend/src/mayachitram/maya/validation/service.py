
from mayachitram.maya.schemas import QualityValidationCheck, QualityValidationReport
from mayachitram.projects.models import Asset
from mayachitram.projects.service import ProjectService


class QualityValidationService:
    """Validation service checking output asset integrity, constraints, and format requirements."""

    def __init__(self, project_service: ProjectService) -> None:
        self.project_service = project_service

    def validate_asset(
        self,
        asset: Asset,
        expected_project_id: str,
        expected_format: str | None = None,
        min_width: int | None = None,
        min_height: int | None = None,
        max_width: int | None = None,
        max_height: int | None = None,
        expected_aspect_ratio: float | None = None,
        aspect_tolerance: float = 0.05,
    ) -> QualityValidationReport:
        checks: list[QualityValidationCheck] = []

        # 1. Verify existence in storage
        exists_check = False
        try:
            file_bytes, _, _ = self.project_service.get_asset_file_bytes(asset.id)
            exists_check = len(file_bytes) > 0
        except Exception:
            exists_check = False

        checks.append(
            QualityValidationCheck(
                name="storage_file_exists",
                passed=exists_check,
                expected="Asset file readable from storage",
                actual="Present" if exists_check else "Missing or unreadable",
                details=f"Verified storage key {asset.storage_key}",
            )
        )

        # 2. Verify project isolation / ownership
        proj_matches = asset.project_id == expected_project_id
        checks.append(
            QualityValidationCheck(
                name="project_ownership",
                passed=proj_matches,
                expected=expected_project_id,
                actual=asset.project_id,
                details="Asset is assigned to the active project boundary",
            )
        )

        # 3. Format constraint
        if expected_format:
            expected_lower = expected_format.lower()
            actual_format = asset.media_type.split("/")[-1].lower()
            format_matches = expected_lower in actual_format or actual_format in expected_lower
            checks.append(
                QualityValidationCheck(
                    name="format_match",
                    passed=format_matches,
                    expected=expected_format,
                    actual=asset.media_type,
                    details=f"Media type verified against expected {expected_format}",
                )
            )

        # 4. Dimension constraints
        if min_width is not None:
            passed = asset.width >= min_width
            checks.append(
                QualityValidationCheck(
                    name="min_width",
                    passed=passed,
                    expected=f">= {min_width}",
                    actual=asset.width,
                    details="Width meets minimum required resolution",
                )
            )

        if min_height is not None:
            passed = asset.height >= min_height
            checks.append(
                QualityValidationCheck(
                    name="min_height",
                    passed=passed,
                    expected=f">= {min_height}",
                    actual=asset.height,
                    details="Height meets minimum required resolution",
                )
            )

        if max_width is not None:
            passed = asset.width <= max_width
            checks.append(
                QualityValidationCheck(
                    name="max_width",
                    passed=passed,
                    expected=f"<= {max_width}",
                    actual=asset.width,
                    details="Width satisfies maximum bound",
                )
            )

        if max_height is not None:
            passed = asset.height <= max_height
            checks.append(
                QualityValidationCheck(
                    name="max_height",
                    passed=passed,
                    expected=f"<= {max_height}",
                    actual=asset.height,
                    details="Height satisfies maximum bound",
                )
            )

        # 5. Aspect ratio check
        if expected_aspect_ratio is not None and asset.height > 0:
            actual_ratio = asset.width / asset.height
            ratio_passed = abs(actual_ratio - expected_aspect_ratio) <= aspect_tolerance
            checks.append(
                QualityValidationCheck(
                    name="aspect_ratio",
                    passed=ratio_passed,
                    expected=f"{expected_aspect_ratio:.2f} ± {aspect_tolerance}",
                    actual=f"{actual_ratio:.2f}",
                    details="Geometry aspect ratio conforms to target delivery specification",
                )
            )

        all_passed = all(c.passed for c in checks)
        summary = (
            f"Quality validation PASSED ({len(checks)}/{len(checks)} checks satisfied)."
            if all_passed
            else f"Quality validation FAILED ({sum(1 for c in checks if not c.passed)} check(s) violated)."
        )

        return QualityValidationReport(
            asset_id=asset.id,
            passed=all_passed,
            checks=checks,
            summary=summary,
        )
