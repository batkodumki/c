from __future__ import annotations

import numpy as np
from numpy.typing import NDArray


def compute_weights(matrix: NDArray[np.float64]) -> NDArray[np.float64]:
    """Обчислює ваги альтернатив методом власного вектора."""
    eigenvalues, eigenvectors = np.linalg.eig(matrix)
    idx = int(np.argmax(eigenvalues.real))
    principal = np.abs(eigenvectors[:, idx].real)
    weights = principal / np.sum(principal)
    return weights

