from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray

from .ranking import compute_weights
from .scales import AVAILABLE_SCALES

RI_TABLE = {
    1: 0.0,
    2: 0.0,
    3: 0.58,
    4: 0.90,
    5: 1.12,
    6: 1.24,
    7: 1.32,
    8: 1.41,
    9: 1.45,
    10: 1.49,
}


@dataclass
class ConsistencyReport:
    lambda_max: float
    ci: float
    cr: float
    threshold: float

    def is_consistent(self) -> bool:
        return self.cr <= self.threshold


@dataclass
class Recommendation:
    title: str
    details: str


def evaluate_consistency(matrix: NDArray[np.float64], threshold: float = 0.1) -> ConsistencyReport:
    n = matrix.shape[0]
    eigenvalues, _ = np.linalg.eig(matrix)
    lambda_max = float(np.max(eigenvalues.real))
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    ri = RI_TABLE.get(n, RI_TABLE[max(RI_TABLE.keys())])
    cr = ci / ri if ri else 0.0
    return ConsistencyReport(lambda_max=lambda_max, ci=ci, cr=cr, threshold=threshold)


JudgmentMap = Dict[Tuple[str, str], Tuple[float, float, str, str]]


def generate_recommendations(
    report: ConsistencyReport,
    matrix: NDArray[np.float64],
    alternatives: List[str],
    judgments: JudgmentMap,
    weights: Optional[NDArray[np.float64]] = None,
) -> List[Recommendation]:
    if report.is_consistent() or len(alternatives) < 2:
        return []

    if weights is None:
        weights = compute_weights(matrix)

    alt_index = {alt: idx for idx, alt in enumerate(alternatives)}

    discrepancies: List[Tuple[float, str, str, float, float, str, str]] = []
    for (ai, aj), (_, _, scale_key, choice_label) in judgments.items():
        i = alt_index.get(ai)
        j = alt_index.get(aj)
        if i is None or j is None:
            continue
        denominator = weights[j]
        if denominator <= 0:
            continue
        expected_ratio = weights[i] / denominator
        if expected_ratio <= 0:
            continue
        actual_ratio = matrix[i, j]
        if actual_ratio <= 0:
            continue
        gap = abs(np.log(actual_ratio / expected_ratio))
        scale_name = (
            AVAILABLE_SCALES.get(scale_key).name if scale_key in AVAILABLE_SCALES else scale_key
        )
        discrepancies.append(
            (
                gap,
                ai,
                aj,
                actual_ratio,
                expected_ratio,
                scale_name,
                choice_label,
            )
        )

    discrepancies.sort(reverse=True, key=lambda item: item[0])

    recommendations: List[Recommendation] = []
    for gap, ai, aj, actual, expected, scale_name, choice_label in discrepancies[:3]:
        recommendations.append(
            Recommendation(
                title=f"Перегляньте пару {ai} ⇔ {aj}",
                details=(
                    "Поточне відношення переваги становить "
                    f"{actual:.3f}, а узгоджене за вагами — {expected:.3f}. "
                    f"Поточний вибір: «{choice_label}» (шкала {scale_name}). "
                    "Спробуйте уточнити градацію у вибраній шкалі для цієї пари."
                ),
            )
        )

    if not recommendations:
        recommendations.append(
            Recommendation(
                title="Перегляньте судження",
                details=(
                    "Переконайтеся, що всі пари оцінено послідовно, та за потреби "
                    "уточніть градації в деталізованіших шкалах (Ма–Чжен, Донаган–Додд–МакМастер)."
                ),
            )
        )
    else:
        recommendations.append(
            Recommendation(
                title="Уточніть шкали",
                details=(
                    "Для пар із найбільшими відхиленнями використайте шкали з більшою "
                    "кількістю градацій або повторно оцініть альтернативи."
                ),
            )
        )

    return recommendations

