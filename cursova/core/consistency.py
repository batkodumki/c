from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from numpy.typing import NDArray

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


def generate_recommendations(
    report: ConsistencyReport,
    alternatives: List[str],
) -> List[Recommendation]:
    if report.is_consistent() or len(alternatives) < 2:
        return []
    return [
        Recommendation(
            title="Перегляньте судження",
            details=(
                "Перевірте пари альтернатив з найбільшою невизначеністю та "
                "уточніть обрані шкали, зокрема для альтернатив у середині ранжування."
            ),
        ),
        Recommendation(
            title="Уточніть шкали",
            details=(
                "Спробуйте використати шкали з більшою градацією (Ма–Чжен або "
                "Донаган–Додд–МакМастер) для пар, де оцінки викликають сумнів."
            ),
        ),
    ]

