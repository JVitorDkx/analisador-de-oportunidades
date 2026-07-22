"""Application service that exposes the deterministic analysis workflow."""

from __future__ import annotations

from pydantic import ValidationError

from src.api.models import (
    AnalysisResponse,
    AnalyzeRequest,
    HealthChecksResponse,
    HealthResponse,
    InputValidationResponse,
)
from src.interpretation import derive_input_status, generate_analysis
from src.pipeline import run_pipeline
from src.scoring.engine import ScoreEngine
from src.validation.validate_input import validate_input
from src.validation.validate_output import validate_output


class InvalidAnalysisInput(ValueError):
    """Raised when a request does not satisfy the versioned input contract."""

    def __init__(self, validation: InputValidationResponse) -> None:
        super().__init__("The analysis input is invalid.")
        self.validation = validation


class AnalysisContractError(RuntimeError):
    """Raised when internally generated data violates an authoritative contract."""


class ServiceUnavailableError(RuntimeError):
    """Raised when a required local service dependency is unavailable."""


def analyze_payload(
    payload: AnalyzeRequest,
    *,
    processed_at: str | None = None,
) -> AnalysisResponse:
    """Run the core workflow and return a globally validated v1.1.0 report."""

    core_payload = payload.model_dump(mode="json", exclude_unset=True)
    pipeline_result = run_pipeline(core_payload)
    try:
        input_validation = InputValidationResponse.model_validate(
            pipeline_result.get("input_validation", {})
        )
    except ValidationError as exc:
        raise AnalysisContractError("The input validator produced an invalid result.") from exc
    if not input_validation.valid:
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
    try:
        return AnalysisResponse.model_validate(analysis)
    except ValidationError as exc:
        raise AnalysisContractError("The generated analysis violates the HTTP response contract.") from exc


def validate_payload(payload: AnalyzeRequest) -> InputValidationResponse:
    """Return the deterministic pre-score validation report for a typed request."""

    validation = validate_input(
        payload.model_dump(mode="json", exclude_unset=True),
        require_official_score=False,
    )
    try:
        return InputValidationResponse.model_validate(validation)
    except ValidationError as exc:
        raise AnalysisContractError("The input validator produced an invalid result.") from exc


def health_status() -> HealthResponse:
    """Verify that the authorized score configuration can be loaded."""

    try:
        engine = ScoreEngine.from_file()
    except (OSError, TypeError, ValueError) as exc:
        raise ServiceUnavailableError("The authorized score configuration is unavailable.") from exc
    if engine.score_version != "SCORE-0.1.0":
        raise ServiceUnavailableError("The authorized score configuration has an unexpected version.")
    return HealthResponse(
        status="ok",
        service="opportunity-analyzer-api",
        api_version="1.0.0",
        score_version="SCORE-0.1.0",
        checks=HealthChecksResponse(core="ok", score_configuration="ok"),
    )
