"""FastAPI application for the Opportunity Analyzer."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import Body, FastAPI, HTTPException, status

from src.api.service import AnalysisContractError, InvalidAnalysisInput, analyze_payload


API_VERSION = "1.0.0"


def create_app() -> FastAPI:
    """Create the ASGI application without modifying the deterministic core."""

    application = FastAPI(
        title="Analisador de Oportunidades API",
        version=API_VERSION,
        description="API REST para o pipeline determinístico e o relatório analítico v1.1.0.",
    )

    @application.post(
        "/api/v1/analyze",
        response_model=dict[str, Any],
        status_code=status.HTTP_200_OK,
        summary="Executar análise completa",
    )
    def analyze(
        payload: Annotated[
            dict[str, Any],
            Body(description="Entrada compatível com references/input-schema.json."),
        ],
    ) -> dict[str, Any]:
        try:
            return analyze_payload(payload)
        except InvalidAnalysisInput as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "invalid_analysis_input",
                    "message": str(exc),
                    "validation": exc.validation,
                },
            ) from exc
        except AnalysisContractError as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "code": "analysis_contract_error",
                    "message": str(exc),
                },
            ) from exc

    return application


app = create_app()
