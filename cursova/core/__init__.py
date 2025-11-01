"""Ядро застосунку для методу попарних порівнянь."""

from .scales import AVAILABLE_SCALES, ScaleDefinition, ScaleOption
from .pcm import build_pairwise_matrix, CardinalLog
from .ranking import compute_weights
from .consistency import (
    ConsistencyReport,
    Recommendation,
    evaluate_consistency,
    generate_recommendations,
)

__all__ = [
    "AVAILABLE_SCALES",
    "ScaleDefinition",
    "ScaleOption",
    "build_pairwise_matrix",
    "CardinalLog",
    "compute_weights",
    "evaluate_consistency",
    "ConsistencyReport",
    "Recommendation",
    "generate_recommendations",
]
