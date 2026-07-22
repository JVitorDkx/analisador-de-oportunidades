"""Deterministic market intelligence isolated from SCORE-0.1.0."""

from src.scoring.offer_intelligence.engine import OfferIntelligenceEngine
from src.scoring.offer_intelligence.models import (
    INTELLIGENCE_VERSION,
    CalculatedIndicatorResult,
    OfferIntelligenceInput,
    OfferIntelligenceResult,
)

__all__ = [
    "INTELLIGENCE_VERSION",
    "CalculatedIndicatorResult",
    "OfferIntelligenceEngine",
    "OfferIntelligenceInput",
    "OfferIntelligenceResult",
]
