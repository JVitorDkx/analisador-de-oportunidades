"""Strict transport models for the versioned HTTP API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue


NonEmptyString = Annotated[str, Field(min_length=1)]
NonNegativeFloat = Annotated[float, Field(ge=0)]
PositiveInteger = Annotated[int, Field(ge=1)]
Percentage = Annotated[float, Field(ge=0, le=100)]
ObservedEvidenceId = Annotated[str, Field(pattern=r"^OBS-[A-Z0-9-]+$")]
CalculatedIndicatorId = Annotated[str, Field(pattern=r"^CALC-[A-Z0-9-]+$")]
EvidenceId = Annotated[str, Field(pattern=r"^(OBS|CALC)-[A-Z0-9-]+$")]
AnalysisMode = Literal["pre_test", "campaign_diagnosis", "reassessment"]
Quality = Literal["high", "medium", "low", "unknown"]
Severity = Literal["low", "medium", "high", "critical"]
RecommendationAction = Literal[
    "prioritize_test",
    "test_with_conditions",
    "collect_more_data",
    "continue_collecting",
    "consider_limited_scale",
    "iterate_creative",
    "iterate_offer",
    "inspect_landing_page",
    "inspect_checkout",
    "pause_for_review",
    "run_controlled_test",
    "deprioritize",
    "reject_for_now",
    "insufficient_data",
]


class StrictTransportModel(BaseModel):
    """Base DTO that rejects fields absent from the HTTP contract."""

    model_config = ConfigDict(extra="forbid")


class UserContextRequest(StrictTransportModel):
    country: Annotated[str, Field(min_length=2)]
    experience_level: Literal["beginner", "intermediate", "advanced"]
    business_model: Literal["ecommerce", "dropshipping", "marketplace", "infoproduct", "affiliate"]
    primary_channel: Literal["meta", "tiktok", "google", "organic", "marketplace", "mixed"]
    test_budget_brl: NonNegativeFloat
    language: str | None = None
    maximum_test_days: PositiveInteger | None = None
    target_margin_percent: Percentage | None = None
    maximum_acceptable_cpa: NonNegativeFloat | None = None
    available_team: list[str] = Field(default_factory=list)
    operational_constraints: list[str] = Field(default_factory=list)
    excluded_categories: list[str] = Field(default_factory=list)
    objectives: list[str] = Field(default_factory=list)


class ObservedEvidenceRequest(StrictTransportModel):
    evidence_id: ObservedEvidenceId
    opportunity_id: NonEmptyString
    source_type: NonEmptyString
    collected_at: datetime
    field: NonEmptyString
    value: JsonValue
    value_type: NonEmptyString
    collection_method: NonEmptyString
    quality: Quality
    source_url: str | None = None
    notes: str | None = None


class CalculatedIndicatorRequest(StrictTransportModel):
    indicator_id: CalculatedIndicatorId
    opportunity_id: NonEmptyString
    field: NonEmptyString
    value: int | float | str | bool | None
    value_type: Literal["integer", "number", "string", "boolean", "null"]
    unit: str | None
    calculation_method: NonEmptyString
    calculation_version: NonEmptyString
    calculated_at: datetime
    source_evidence_ids: list[ObservedEvidenceId]
    quality: Quality
    warnings: list[NonEmptyString]


class DataQualityRequest(StrictTransportModel):
    status: Literal["complete", "partial", "weak", "invalid"]
    coverage_percent: Percentage
    freshness: Literal["current", "aging", "stale", "unknown"]
    source_agreement: Quality


class ScoringContextRequest(StrictTransportModel):
    economic_inputs_evidence_id: ObservedEvidenceId
    minimum_test_cost_evidence_id: ObservedEvidenceId
    operator_budget_evidence_id: ObservedEvidenceId
    operational_fit_evidence_id: ObservedEvidenceId
    independent_source_ids: list[NonEmptyString]
    calculation_quality: Quality
    logistics_evidence_id: ObservedEvidenceId | None = None


class StructuredRiskFlag(StrictTransportModel):
    code: NonEmptyString
    severity: Severity


class OpportunityRequest(StrictTransportModel):
    opportunity_id: NonEmptyString
    name: NonEmptyString
    observed_evidence: Annotated[list[ObservedEvidenceRequest], Field(min_length=1)]
    calculated_indicators: list[CalculatedIndicatorRequest]
    data_quality: DataQualityRequest
    category: str | None = None
    description: str | None = None
    source_urls: list[str] = Field(default_factory=list)
    campaign_metrics: dict[str, JsonValue] | None = None
    collection_errors: list[str] = Field(default_factory=list)
    risk_flags: list[str | StructuredRiskFlag] = Field(default_factory=list)
    scoring_context: ScoringContextRequest | None = None


class ScoreConfigurationRequest(StrictTransportModel):
    version: NonEmptyString
    weights: dict[str, float]
    calculation_timestamp: datetime
    engine: NonEmptyString


class AnalyzeRequest(StrictTransportModel):
    schema_version: Literal["1.0.0"]
    analysis_id: NonEmptyString
    generated_at: datetime
    analysis_mode: AnalysisMode
    user_context: UserContextRequest
    opportunities: Annotated[list[OpportunityRequest], Field(min_length=1)]
    score_configuration: ScoreConfigurationRequest
    requested_output_language: NonEmptyString


class SecurityStatusResponse(StrictTransportModel):
    prompt_injection_detected: bool
    suspicious_fields: list[str]
    sensitive_data_detected: bool


class VersionsResponse(StrictTransportModel):
    skill_version: Literal["1.1.0"]
    input_schema_version: Literal["1.0.0"]
    output_schema_version: Literal["1.1.0"]
    score_version: NonEmptyString


class ContextAssessmentResponse(StrictTransportModel):
    fit: Literal["strong_fit", "acceptable_fit", "conditional_fit", "poor_fit", "unknown"]
    budget_compatibility: Literal["compatible", "conditional", "incompatible", "unknown"]
    channel_compatibility: Literal["strong", "moderate", "weak", "unknown"]
    operational_constraints: list[str]
    explanation: str


class EvidenceStatementResponse(StrictTransportModel):
    statement: str
    evidence_ids: list[EvidenceId]


class RiskResponse(StrictTransportModel):
    risk: str
    severity: Severity
    evidence_ids: list[EvidenceId]


class ModuleAssessmentsResponse(StrictTransportModel):
    operator_context: str
    validation: str
    offer_economics: str
    traffic: str | None
    trends: str


class RankingItemResponse(StrictTransportModel):
    position: PositiveInteger
    opportunity_id: NonEmptyString
    official_score: float | None
    official_score_scale: str | None
    official_score_rank: PositiveInteger | None
    contextual_recommendation_rank: PositiveInteger
    context_fit: Literal["strong_fit", "acceptable_fit", "conditional_fit", "poor_fit", "unknown"]
    strengths: list[EvidenceStatementResponse]
    weaknesses: list[EvidenceStatementResponse]
    risks: list[RiskResponse]
    module_assessments: ModuleAssessmentsResponse
    evidence_ids: list[EvidenceId]


class InferenceResponse(StrictTransportModel):
    inference_id: Annotated[str, Field(pattern=r"^INF-[A-Z0-9-]+$")]
    statement: str
    evidence_ids: list[EvidenceId]
    certainty: Literal["strong", "moderate", "weak"]


class RequiredEvidenceResponse(StrictTransportModel):
    opportunity_id: NonEmptyString
    field: NonEmptyString
    reason: NonEmptyString


class RecommendationResponse(StrictTransportModel):
    recommendation_id: Annotated[str, Field(pattern=r"^REC-[A-Z0-9-]+$")]
    opportunity_id: NonEmptyString
    action: RecommendationAction
    statement: NonEmptyString
    rationale: NonEmptyString
    evidence_ids: Annotated[list[EvidenceId], Field(min_length=1)]
    risks: list[str]
    minimum_action: NonEmptyString
    success_metrics: list[str]
    stop_conditions: list[str]
    required_evidence: list[RequiredEvidenceResponse]


class SourceConflictResponse(StrictTransportModel):
    description: str
    evidence_ids: list[EvidenceId]
    impact: Literal["low", "medium", "high"]
    resolution_data_needed: list[str]


class MissingDataResponse(StrictTransportModel):
    field: str
    importance: Severity
    reason: str
    collection_suggestion: str


class CalculationWarningResponse(StrictTransportModel):
    calculation_id: CalculatedIndicatorId
    warning: str
    action: Literal["calculation_review_required"]


class NextExperimentResponse(StrictTransportModel):
    experiment_id: NonEmptyString
    objective: NonEmptyString
    hypothesis: NonEmptyString
    primary_variable: NonEmptyString
    control_variable: str | None
    minimum_action: NonEmptyString
    maximum_budget: NonNegativeFloat | None
    currency: NonEmptyString
    duration_days: PositiveInteger | None
    success_metrics: list[str]
    success_conditions: list[str]
    stop_conditions: list[str]
    required_feedback_fields: list[str]


class HumanReviewResponse(StrictTransportModel):
    required: bool
    reasons: list[str]


class AnalysisResponse(StrictTransportModel):
    schema_version: Literal["1.1.0"]
    analysis_id: NonEmptyString
    analysis_mode: AnalysisMode
    processed_at: datetime
    input_status: Literal["sufficient", "partial", "insufficient", "invalid"]
    security_status: SecurityStatusResponse
    versions: VersionsResponse
    recommended_opportunity_id: str | None
    recommendation: RecommendationAction
    confidence: Literal["high", "moderate", "low", "inconclusive"]
    executive_summary: str
    context_assessment: ContextAssessmentResponse
    ranking: list[RankingItemResponse]
    favorable_evidence: list[EvidenceStatementResponse]
    contrary_evidence: list[EvidenceStatementResponse]
    inferences: list[InferenceResponse]
    recommendations: list[RecommendationResponse]
    source_conflicts: list[SourceConflictResponse]
    missing_data: list[MissingDataResponse]
    calculation_warnings: list[CalculationWarningResponse]
    next_experiment: NextExperimentResponse
    conditions_that_would_change_recommendation: list[str]
    human_review: HumanReviewResponse
    disclaimer: str


class ValidationIssueResponse(StrictTransportModel):
    code: NonEmptyString
    path: NonEmptyString
    message: NonEmptyString
    severity: Literal["error", "warning"]


class InputValidationResponse(StrictTransportModel):
    status: Literal["valid", "invalid", "partial", "sufficient"]
    valid: bool
    error_count: Annotated[int, Field(ge=0)]
    warning_count: Annotated[int, Field(ge=0)]
    issues: list[ValidationIssueResponse]


class ProblemError(StrictTransportModel):
    pointer: NonEmptyString
    code: NonEmptyString
    detail: NonEmptyString


class ProblemDetail(StrictTransportModel):
    type: NonEmptyString
    title: NonEmptyString
    status: Annotated[int, Field(ge=400, le=599)]
    detail: NonEmptyString
    instance: NonEmptyString
    code: NonEmptyString
    request_id: NonEmptyString
    errors: list[ProblemError] = Field(default_factory=list)


class HealthChecksResponse(StrictTransportModel):
    core: Literal["ok"]
    score_configuration: Literal["ok"]


class HealthResponse(StrictTransportModel):
    status: Literal["ok"]
    service: Literal["opportunity-analyzer-api"]
    api_version: Literal["1.0.0"]
    score_version: Literal["SCORE-0.1.0"]
    checks: HealthChecksResponse
