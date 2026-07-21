"""Command-line interface for the complete Opportunity Analyst workflow."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from src.interpretation import derive_input_status, generate_analysis
from src.pipeline import run_pipeline_file
from src.validation.validate_output import validate_output


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa scoring, interpretação INF/REC e validação final.",
    )
    parser.add_argument("--input", required=True, help="Arquivo JSON de entrada.")
    parser.add_argument("--output", required=True, help="Destino do relatório JSON validado.")
    return parser


def _print_pipeline_errors(pipeline_result: dict[str, Any], stream: TextIO) -> None:
    print("Não foi possível concluir a análise.", file=stream)
    validation = pipeline_result.get("input_validation", {})
    for issue in validation.get("issues", []):
        if isinstance(issue, dict):
            print(
                f"- {issue.get('path', '$')}: {issue.get('message', issue.get('code', 'erro'))}",
                file=stream,
            )
    for result in pipeline_result.get("opportunity_results", []):
        if not isinstance(result, dict) or result.get("status") != "input_error":
            continue
        for issue in result.get("eligibility_issues", []):
            print(f"- {result.get('opportunity_id')}: {issue}", file=stream)


def _print_summary(
    analysis: dict[str, Any],
    pipeline_result: dict[str, Any],
    output_path: Path,
    stream: TextIO,
) -> None:
    print("Analisador de Oportunidades", file=stream)
    print(f"Análise: {analysis['analysis_id']}", file=stream)
    print(f"Status: {analysis['input_status']}", file=stream)
    print(f"Confiança: {analysis['confidence']}", file=stream)
    print("", file=stream)
    print("Scores oficiais:", file=stream)
    for result in pipeline_result.get("opportunity_results", []):
        if not isinstance(result, dict):
            continue
        score = result.get("official_score_display")
        score_text = score if score is not None else "indisponível"
        print(
            f"- {result.get('opportunity_id')}: {score_text} ({result.get('status')})",
            file=stream,
        )

    triggered = [
        (result.get("opportunity_id"), switch.get("reason"))
        for result in pipeline_result.get("opportunity_results", [])
        if isinstance(result, dict)
        for switch in result.get("kill_switches", [])
        if isinstance(switch, dict) and switch.get("triggered") is True
    ]
    print("", file=stream)
    print("Kill switches:", file=stream)
    if triggered:
        for opportunity_id, reason in triggered:
            print(f"- {opportunity_id}: {reason}", file=stream)
    else:
        print("- nenhum acionado", file=stream)

    warnings = [
        (result.get("opportunity_id"), warning)
        for result in pipeline_result.get("opportunity_results", [])
        if isinstance(result, dict)
        for warning in result.get("warnings", [])
    ]
    print("", file=stream)
    print("Avisos:", file=stream)
    if warnings:
        for opportunity_id, warning in warnings:
            print(f"- {opportunity_id}: {warning}", file=stream)
    else:
        print("- nenhum", file=stream)

    print("", file=stream)
    print(f"Recomendação principal: {analysis['recommendation']}", file=stream)
    for recommendation in analysis.get("recommendations", []):
        print(
            f"- {recommendation['recommendation_id']} / {recommendation['opportunity_id']}: "
            f"{recommendation['action']} — {recommendation['statement']}",
            file=stream,
        )
    print(f"Saída validada: {output_path}", file=stream)


def run_cli(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    processed_at: str | None = None,
) -> int:
    """Run the complete workflow and return a process-compatible exit code."""

    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr
    args = _parser().parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)

    pipeline_result = run_pipeline_file(input_path)
    if pipeline_result.get("status") == "invalid" or not isinstance(
        pipeline_result.get("enriched_input"),
        dict,
    ):
        _print_pipeline_errors(pipeline_result, error_stream)
        return 1

    try:
        analysis = generate_analysis(pipeline_result, processed_at=processed_at)
        validation = validate_output(
            analysis,
            pipeline_result["enriched_input"],
            expected_input_status=derive_input_status(pipeline_result),
        )
        if not validation["valid"]:
            print("A saída gerada falhou na validação global.", file=error_stream)
            for issue in validation["issues"]:
                print(f"- {issue['path']}: {issue['message']}", file=error_stream)
            return 1
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(analysis, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except (OSError, TypeError, ValueError) as exc:
        print(f"Falha ao gerar a análise: {exc}", file=error_stream)
        return 1

    _print_summary(analysis, pipeline_result, output_path, output_stream)
    return 0


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
