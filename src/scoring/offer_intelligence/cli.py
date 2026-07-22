"""Independent CLI for OFFER-INTELLIGENCE-0.1.0."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any, TextIO

from pydantic import ValidationError

from src.scoring.offer_intelligence.engine import OfferIntelligenceEngine
from src.scoring.offer_intelligence.models import (
    OfferIntelligenceInput,
    OfferIntelligenceResult,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Executa o pacote determinístico OFFER-INTELLIGENCE-0.1.0.",
    )
    parser.add_argument("--input", required=True, help="Arquivo JSON de inteligência de ofertas.")
    parser.add_argument("--output", required=True, help="Destino do envelope JSON validado.")
    return parser


def _load_input(path: Path) -> OfferIntelligenceInput:
    data = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
    return OfferIntelligenceInput.model_validate(data)


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            handle.write(serialized)
            temporary_path = Path(handle.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def _display_value(value: Decimal, precision: int) -> str:
    if value == value.to_integral_value():
        return str(int(value))
    return f"{value:.{precision}f}"


def _print_summary(
    result: OfferIntelligenceResult,
    output_path: Path,
    precision: int,
    stream: TextIO,
) -> None:
    print("Offer Intelligence", file=stream)
    print(f"Análise: {result.analysis_id}", file=stream)
    print(f"Oportunidade: {result.opportunity_id}", file=stream)
    print(f"Status: {result.status}", file=stream)
    print("", file=stream)
    print("Indicadores:", file=stream)
    if result.indicators:
        for indicator in result.indicators:
            print(
                f"- {indicator.indicator_id}: "
                f"{_display_value(indicator.value, precision)} {indicator.unit}",
                file=stream,
            )
    else:
        print("- nenhum", file=stream)

    print("", file=stream)
    print("Dados necessários:", file=stream)
    if result.missing_inputs:
        for missing in result.missing_inputs:
            print(
                f"- {missing.indicator_field}: {', '.join(missing.required_inputs)}",
                file=stream,
            )
    else:
        print("- nenhum", file=stream)

    print("", file=stream)
    print("Avisos:", file=stream)
    if result.warnings:
        for warning in result.warnings:
            print(f"- {warning.code}: {warning.message}", file=stream)
    else:
        print("- nenhum", file=stream)
    print(f"Saída validada: {output_path}", file=stream)


def run_cli(
    argv: list[str] | None = None,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    engine: OfferIntelligenceEngine | None = None,
) -> int:
    """Run the isolated engine and return a process-compatible exit code."""

    output_stream = stdout or sys.stdout
    error_stream = stderr or sys.stderr
    args = _parser().parse_args(argv)
    input_path = Path(args.input)
    output_path = Path(args.output)

    try:
        payload = _load_input(input_path)
    except (OSError, json.JSONDecodeError, ValidationError, ValueError) as exc:
        print(f"Entrada inválida de Offer Intelligence: {exc}", file=error_stream)
        return 2

    try:
        intelligence_engine = engine or OfferIntelligenceEngine.from_file()
        result = intelligence_engine.analyze(payload)
        _write_json_atomic(output_path, result.as_dict())
    except (OSError, ValidationError, TypeError, ValueError) as exc:
        print(f"Falha ao executar Offer Intelligence: {exc}", file=error_stream)
        return 1

    _print_summary(
        result,
        output_path,
        intelligence_engine.config.scale.display_precision,
        output_stream,
    )
    return 0


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
