from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np

from .scales import ratio_from_cardinal


@dataclass
class CardinalLogEntry:
    alternative_i: str
    alternative_j: str
    scale: str
    choice: str
    cardinal_value: float
    ratio_value: float


CardinalLog = List[CardinalLogEntry]


def build_pairwise_matrix(
    alternatives: List[str],
    judgments: Dict[Tuple[str, str], Tuple[float, float, str, str]],
) -> Tuple[np.ndarray, CardinalLog]:
    """Створює матрицю попарних порівнянь.

    judgments[(ai, aj)] = (cardinal_value, ratio_value, scale_key, choice_label)
    """

    n = len(alternatives)
    matrix = np.ones((n, n))
    logs: CardinalLog = []
    alt_index = {alt: idx for idx, alt in enumerate(alternatives)}

    for (ai, aj), (cardinal, ratio, scale_key, choice_label) in judgments.items():
        i = alt_index[ai]
        j = alt_index[aj]
        matrix[i, j] = ratio
        matrix[j, i] = 1.0 / ratio
        logs.append(
            CardinalLogEntry(
                alternative_i=ai,
                alternative_j=aj,
                scale=scale_key,
                choice=choice_label,
                cardinal_value=cardinal,
                ratio_value=ratio,
            )
        )

    return matrix, logs


def default_ratio(cardinal_value: float) -> float:
    return ratio_from_cardinal(cardinal_value)

