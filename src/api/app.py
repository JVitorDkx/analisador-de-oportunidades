"""FastAPI application for the Opportunity Analyzer."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import Body, Depends, FastAPI, Header, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.responses import Response

from src.api.auth import (
    ApiAuthenticationError,
    ApiSecurityDependencies,
    ApiSecurityUnavailable,
    AuthenticatedSession,
    authenticate_session,
    production_api_security_dependencies,
)
from src.api.config import demo_mode_enabled
from src.api.models import (
    AnalysisDetailResponse,
    AnalysisHistoryResponse,
    AnalysisResponse,
    AnalyzeRequest,
    DashboardResponse,
    HealthResponse,
    InputValidationResponse,
    ProblemDetail,
    ProblemError,
    SessionResponse,
)
from src.api.persistence import (
    AnalysisNotFound,
    AnalysisPersistenceDenied,
    AnalysisPersistenceUnavailable,
    AnalysisQuotaExceeded,
    AnalysisRepository,
    execute_persisted_analysis,
    production_analysis_repository,
)
from src.api.service import (
    AnalysisContractError,
    InvalidAnalysisInput,
    ServiceUnavailableError,
    analyze_payload,
    health_status,
    validate_payload,
)


API_VERSION = "1.0.0"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
PROBLEM_TYPE_PREFIX = "urn:problem:opportunity-analyzer"
logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="SupabaseBearer",
    description="Supabase Auth access token verified through the project JWKS.",
)


def _fixture_examples() -> dict[str, dict[str, object]]:
    cases = (
        ("viable", "Oportunidade viável", "opportunity_viable.json"),
        ("kill_switch", "Oportunidade reprovada por kill switch", "opportunity_kill_switch.json"),
        ("insufficient_data", "Oportunidade com dados insuficientes", "opportunity_insufficient_data.json"),
    )
    return {
        key: {
            "summary": summary,
            "value": json.loads((PROJECT_ROOT / "fixtures" / "cases" / filename).read_text(encoding="utf-8")),
        }
        for key, summary, filename in cases
    }


FIXTURE_EXAMPLES = _fixture_examples()


def _request_id_header_spec() -> dict[str, object]:
    return {
        "description": "Identificador de rastreabilidade recebido ou gerado pela API.",
        "schema": {"type": "string", "minLength": 1, "maxLength": 128},
    }


def _problem_response_spec(description: str) -> dict[str, object]:
    return {
        "description": description,
        "headers": {"X-Request-ID": _request_id_header_spec()},
        "content": {
            "application/problem+json": {
                "schema": ProblemDetail.model_json_schema(),
            }
        },
    }


def _request_id(request: Request) -> str:
    value = getattr(request.state, "request_id", None)
    return value if isinstance(value, str) else str(uuid4())


def _problem_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    title: str,
    detail: str,
    errors: list[ProblemError] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    problem = ProblemDetail(
        type=f"{PROBLEM_TYPE_PREFIX}:{code}",
        title=title,
        status=status_code,
        detail=detail,
        instance=f"urn:request:{request_id}",
        code=code,
        request_id=request_id,
        errors=errors or [],
    )
    return JSONResponse(
        status_code=status_code,
        content=problem.model_dump(mode="json"),
        media_type="application/problem+json",
    )


def _validation_pointer(location: tuple[str | int, ...]) -> str:
    parts = location[1:] if location and location[0] == "body" else location
    pointer = "$"
    for part in parts:
        pointer += f"[{part}]" if isinstance(part, int) else f".{part}"
    return pointer


def create_app(
    *,
    security: ApiSecurityDependencies | None = None,
    analysis_repository: AnalysisRepository | None = None,
    demo_mode: bool | None = None,
) -> FastAPI:
    """Create the ASGI application without modifying the deterministic core."""

    resolved_demo_mode = False if demo_mode is None else demo_mode
    application = FastAPI(
        title="Analisador de Oportunidades API",
        version=API_VERSION,
        description="API REST para o pipeline determinístico e o relatório analítico v1.1.0.",
        openapi_version="3.1.0",
    )

    def protected_session(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    ) -> AuthenticatedSession:
        dependencies = security
        if dependencies is None:
            dependencies = production_api_security_dependencies()
        authorization = (
            f"{credentials.scheme} {credentials.credentials}"
            if credentials is not None
            else None
        )
        return authenticate_session(
            dependencies,
            authorization=authorization,
            tenant_id=x_tenant_id,
        )

    def persistence_repository() -> AnalysisRepository:
        return analysis_repository or production_analysis_repository()

    def analysis_session(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        x_tenant_id: Annotated[str | None, Header(alias="X-Tenant-ID")] = None,
    ) -> AuthenticatedSession | None:
        if resolved_demo_mode:
            return None
        return protected_session(credentials, x_tenant_id)

    @application.middleware("http")
    async def add_request_id(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        request.state.request_id = incoming if REQUEST_ID_PATTERN.fullmatch(incoming) else str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.exception_handler(RequestValidationError)
    async def request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            ProblemError(
                pointer=_validation_pointer(tuple(error.get("loc", ()))),
                code=str(error.get("type", "validation_error")),
                detail=str(error.get("msg", "Invalid request value.")),
            )
            for error in exc.errors()
        ]
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="request_validation_error",
            title="Request validation failed",
            detail="The request body does not satisfy the typed API contract.",
            errors=errors,
        )

    @application.exception_handler(InvalidAnalysisInput)
    async def invalid_analysis_input(
        request: Request,
        exc: InvalidAnalysisInput,
    ) -> JSONResponse:
        errors = [
            ProblemError(pointer=issue.path, code=issue.code, detail=issue.message)
            for issue in exc.validation.issues
        ]
        return _problem_response(
            request,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="invalid_analysis_input",
            title="Analysis input is invalid",
            detail=str(exc),
            errors=errors,
        )

    @application.exception_handler(ApiAuthenticationError)
    async def authentication_error(
        request: Request,
        exc: ApiAuthenticationError,
    ) -> JSONResponse:
        logger.info("Authentication denied [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="authentication_required",
            title="Authentication required",
            detail="A valid Supabase user session and tenant selection are required.",
        )

    @application.exception_handler(ApiSecurityUnavailable)
    async def security_unavailable(
        request: Request,
        exc: ApiSecurityUnavailable,
    ) -> JSONResponse:
        logger.error("Authentication unavailable [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="authentication_unavailable",
            title="Authentication unavailable",
            detail="The service cannot safely verify tenant identity at this time.",
        )

    @application.exception_handler(AnalysisPersistenceDenied)
    async def persistence_denied(
        request: Request,
        exc: AnalysisPersistenceDenied,
    ) -> JSONResponse:
        logger.info("Analysis persistence denied [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="authentication_required",
            title="Authentication required",
            detail="A valid Supabase user session and tenant selection are required.",
        )

    @application.exception_handler(AnalysisQuotaExceeded)
    async def quota_exceeded(
        request: Request,
        exc: AnalysisQuotaExceeded,
    ) -> JSONResponse:
        logger.info("Analysis quota exceeded [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="analysis_quota_exceeded",
            title="Analysis quota exceeded",
            detail="The tenant has reached its current monthly analysis limit.",
        )

    @application.exception_handler(AnalysisPersistenceUnavailable)
    async def persistence_unavailable(
        request: Request,
        exc: AnalysisPersistenceUnavailable,
    ) -> JSONResponse:
        logger.error("Analysis persistence unavailable [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="analysis_persistence_unavailable",
            title="Analysis persistence unavailable",
            detail="The service cannot safely persist analysis history at this time.",
        )

    @application.exception_handler(AnalysisNotFound)
    async def analysis_not_found(
        request: Request,
        exc: AnalysisNotFound,
    ) -> JSONResponse:
        logger.info("Analysis not found [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_404_NOT_FOUND,
            code="analysis_not_found",
            title="Analysis not found",
            detail="The requested analysis is not available to this tenant.",
        )

    @application.exception_handler(AnalysisContractError)
    async def analysis_contract_error(
        request: Request,
        exc: AnalysisContractError,
    ) -> JSONResponse:
        logger.error("Analysis contract error [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="analysis_contract_error",
            title="Analysis contract failure",
            detail="The service could not produce a response that satisfies its authoritative contract.",
        )

    @application.exception_handler(ServiceUnavailableError)
    async def service_unavailable(
        request: Request,
        exc: ServiceUnavailableError,
    ) -> JSONResponse:
        logger.error("Service unavailable [%s]: %s", _request_id(request), exc)
        return _problem_response(
            request,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="service_unavailable",
            title="Service unavailable",
            detail="A required local service dependency is unavailable.",
        )

    @application.exception_handler(Exception)
    async def unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        logger.exception("Unexpected API error [%s]", _request_id(request), exc_info=exc)
        return _problem_response(
            request,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="internal_server_error",
            title="Internal server error",
            detail="The service encountered an unexpected error while processing the request.",
        )

    @application.get(
        "/api/v1/health",
        response_model=HealthResponse,
        operation_id="getHealth",
        summary="Verificar saúde da API",
        responses={
            200: {
                "description": "API e configuração determinística disponíveis.",
                "headers": {"X-Request-ID": _request_id_header_spec()},
            },
            503: _problem_response_spec("A configuração autorizada do core está indisponível."),
        },
    )
    def health() -> HealthResponse:
        return health_status()

    @application.get(
        "/api/v1/session",
        response_model=SessionResponse,
        operation_id="getSession",
        summary="Obter sessão e plano efetivos",
        responses={
            200: {
                "description": "Identidade, tenant, função e plano derivados no servidor.",
                "headers": {"X-Request-ID": _request_id_header_spec()},
            },
            401: _problem_response_spec("O JWT ou o tenant selecionado não são válidos."),
            422: _problem_response_spec("Um cabeçalho da sessão não satisfaz o contrato HTTP."),
            503: _problem_response_spec("A autenticação ou a consulta de assinatura está indisponível."),
        },
    )
    def session(
        authenticated: AuthenticatedSession = Depends(protected_session),
    ) -> SessionResponse:
        return SessionResponse(
            user_id=authenticated.principal.user_id,
            tenant_id=authenticated.principal.tenant_id,
            role=authenticated.principal.role,
            tier=authenticated.entitlement.tier,
            monthly_analysis_limit=authenticated.entitlement.monthly_analysis_limit,
            history_retention_days=authenticated.entitlement.history_retention_days,
        )

    def tenant_principal(
        tenant_id: UUID,
        authenticated: AuthenticatedSession,
    ):
        if str(tenant_id) != authenticated.principal.tenant_id:
            raise AnalysisNotFound("tenant resource not found")
        return authenticated.principal

    @application.get(
        "/api/v1/tenants/{tenant_id}/analyses",
        response_model=AnalysisHistoryResponse,
        operation_id="listTenantAnalyses",
        summary="Listar histórico de análises do tenant",
        responses={
            200: {"description": "Histórico paginado e limitado pela retenção do plano."},
            401: _problem_response_spec("A sessão não é válida."),
            404: _problem_response_spec("O tenant não está disponível para a sessão."),
            422: _problem_response_spec("A paginação ou o identificador é inválido."),
            503: _problem_response_spec("O histórico está temporariamente indisponível."),
        },
    )
    def list_tenant_analyses(
        tenant_id: UUID,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        offset: Annotated[int, Query(ge=0)] = 0,
        authenticated: AuthenticatedSession = Depends(protected_session),
        repository: AnalysisRepository = Depends(persistence_repository),
    ) -> AnalysisHistoryResponse:
        principal = tenant_principal(tenant_id, authenticated)
        return repository.list_history(principal, limit=limit, offset=offset)

    @application.get(
        "/api/v1/tenants/{tenant_id}/analyses/{analysis_id}",
        response_model=AnalysisDetailResponse,
        operation_id="getTenantAnalysis",
        summary="Obter uma análise salva",
        responses={
            200: {"description": "Relatório validado salvo no histórico."},
            401: _problem_response_spec("A sessão não é válida."),
            404: _problem_response_spec("A análise não existe ou não está visível."),
            422: _problem_response_spec("Um identificador é inválido."),
            503: _problem_response_spec("O histórico está temporariamente indisponível."),
        },
    )
    def get_tenant_analysis(
        tenant_id: UUID,
        analysis_id: UUID,
        authenticated: AuthenticatedSession = Depends(protected_session),
        repository: AnalysisRepository = Depends(persistence_repository),
    ) -> AnalysisDetailResponse:
        principal = tenant_principal(tenant_id, authenticated)
        return repository.get_analysis(principal, analysis_id=analysis_id)

    @application.get(
        "/api/v1/tenants/{tenant_id}/dashboard",
        response_model=DashboardResponse,
        operation_id="getTenantDashboard",
        summary="Obter métricas consolidadas do tenant",
        responses={
            200: {"description": "Métricas reais de histórico, plano e quota."},
            401: _problem_response_spec("A sessão não é válida."),
            404: _problem_response_spec("O tenant não está disponível para a sessão."),
            422: _problem_response_spec("O identificador do tenant é inválido."),
            503: _problem_response_spec("As métricas estão temporariamente indisponíveis."),
        },
    )
    def get_tenant_dashboard(
        tenant_id: UUID,
        authenticated: AuthenticatedSession = Depends(protected_session),
        repository: AnalysisRepository = Depends(persistence_repository),
    ) -> DashboardResponse:
        principal = tenant_principal(tenant_id, authenticated)
        return repository.get_dashboard(principal)

    @application.post(
        "/api/v1/validate-input",
        response_model=InputValidationResponse,
        operation_id="validateOpportunityInput",
        summary="Validar entrada sem executar o score",
        responses={
            200: {
                "description": "Resultado tipado da validação de entrada.",
                "headers": {"X-Request-ID": _request_id_header_spec()},
            },
            401: _problem_response_spec("O JWT ou o tenant selecionado não são válidos."),
            422: _problem_response_spec("O corpo não satisfaz o contrato HTTP tipado."),
            500: _problem_response_spec("O validador interno violou seu contrato de resposta."),
            503: _problem_response_spec("A autenticação ou a consulta de assinatura está indisponível."),
        },
    )
    def validate_input_endpoint(
        payload: AnnotatedAnalyzeRequest,
        _authenticated: AuthenticatedSession = Depends(protected_session),
    ) -> InputValidationResponse:
        return validate_payload(payload)

    @application.post(
        "/api/v1/analyze",
        response_model=AnalysisResponse,
        operation_id="analyzeOpportunity",
        status_code=status.HTTP_200_OK,
        summary="Executar análise completa",
        responses={
            200: {
                "description": "Relatório analítico v1.1.0 validado.",
                "headers": {"X-Request-ID": _request_id_header_spec()},
            },
            401: _problem_response_spec("O JWT ou o tenant selecionado não são válidos."),
            422: _problem_response_spec("A entrada é estrutural ou semanticamente inválida."),
            429: _problem_response_spec("A quota mensal de análises do tenant foi atingida."),
            500: _problem_response_spec("A análise gerada violou um contrato autoritativo."),
            503: _problem_response_spec("A autenticação ou a consulta de assinatura está indisponível."),
        },
    )
    def analyze(
        payload: AnnotatedAnalyzeRequest,
        response: Response,
        _authenticated: AuthenticatedSession | None = Depends(analysis_session),
        idempotency_key: Annotated[
            str | None,
            Header(
                alias="Idempotency-Key",
                min_length=8,
                max_length=128,
                pattern=r"^[A-Za-z0-9._:-]+$",
            ),
        ] = None,
    ) -> AnalysisResponse:
        if resolved_demo_mode:
            response.headers["X-Demo-Mode"] = "true"
            return analyze_payload(payload)
        if _authenticated is None:
            raise ApiAuthenticationError("authenticated session is required")
        return execute_persisted_analysis(
            repository=persistence_repository(),
            principal=_authenticated.principal,
            idempotency_key=idempotency_key or f"analysis:{payload.analysis_id}",
            payload=payload,
            analyze=analyze_payload,
        )

    return application


AnnotatedAnalyzeRequest = Annotated[
    AnalyzeRequest,
    Body(
        description="Entrada compatível com references/input-schema.json.",
        openapi_examples=FIXTURE_EXAMPLES,
    ),
]


app = create_app(demo_mode=demo_mode_enabled())
