"""Application service that exposes the deterministic analysis workflow."""

from __future__ import annotations

from typing import Any

from src.interpretation import derive_input_status, generate_analysis
from src.pipeline import run_pipeline
from src.validation.validate_output import validate_output


class InvalidAnalysisInput(ValueError):
    """Raised when a request does not satisfy the versioned input contract."""

    def __init__(self, validation: dict[str, Any]) -> None:
        super().__init__("The analysis input is invalid.")
        self.validation = validation


class AnalysisContractError(RuntimeError):
    """Raised when internally generated data violates an authoritative contract."""


def analyze_payload(
    payload: dict[str, Any],
    *,
    processed_at: str | None = None,
) -> dict[str, Any]:
    """Run the core workflow and return a globally validated v1.1.0 report."""

    pipeline_result = run_pipeline(payload)
    input_validation = pipeline_result.get("input_validation", {})
    if not input_validation.get("valid"):
        raise InvalidAnalysisInput(input_validation)

    if (
        pipeline_result.get("status") == "invalid"
        or not pipeline_result.get("pipeline_validation", {}).get("valid")
        or not isinstance(pipeline_result.get("enriched_input"), dict)
    ):
        raise AnalysisContractError("The deterministic pipeline produced an invalid envelope.")

    analysis = generate_analysis(pipeline_result, processed_at=processed_at)
    output_validation = validate_output(
        analysis,
        pipeline_result["enriched_input"],
        expected_input_status=derive_input_status(pipeline_result),
    )
    if not output_validation.get("valid"):
        raise AnalysisContractError("The generated analysis failed global validation.")
    return analysis
