from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(frozen=True)
class ScaleOption:
    label: str
    cardinal_value: float


@dataclass(frozen=True)
class ScaleDefinition:
    key: str
    name: str
    description: str
    options: Tuple[ScaleOption, ...]

    def to_cardinal(self, label: str) -> float:
        for option in self.options:
            if option.label == label:
                return option.cardinal_value
        raise ValueError(f"Невідомий вибір '{label}' для шкали {self.key}")


def _ordinal_scale() -> ScaleDefinition:
    options = (
        ScaleOption("Перевага першої альтернативи", 8.5),
        ScaleOption("Рівнозначні", 5.5),
        ScaleOption("Перевага другої альтернативи", 2.5),
    )
    return ScaleDefinition(
        key="ordinal",
        name="Порядкова",
        description="Порядкові судження без уточнення ступеня переваги",
        options=options,
    )


def _integer_scale() -> ScaleDefinition:
    options = tuple(
        ScaleOption(f"{i} – перевага першої", 5.5 + (i - 1) * 0.5) for i in range(1, 10)
    ) + (
        ScaleOption("Рівність", 5.5),
    ) + tuple(
        ScaleOption(f"{i} – перевага другої", 5.5 - (i - 1) * 0.5) for i in range(1, 10)
    )
    # Уникнути дублювання центральної точки
    options = tuple({opt.label: opt for opt in options}.values())
    return ScaleDefinition(
        key="integer",
        name="Цілочислова (9 градацій)",
        description="Цілочислова шкала Сааті з дев'ятьма градаціями",
        options=options,
    )


def _balanced_scale() -> ScaleDefinition:
    labels = {
        3: 6.5,
        4: 7.0,
        5: 7.5,
        6: 8.0,
        7: 8.5,
        8: 9.0,
        9: 9.5,
    }
    options = tuple(
        ScaleOption(f"{k} – перша краще", v) for k, v in labels.items()
    ) + (
        ScaleOption("Рівнозначні", 5.5),
    ) + tuple(
        ScaleOption(f"{k} – друга краще", 11 - v) for k, v in labels.items()
    )
    return ScaleDefinition(
        key="balanced",
        name="Збалансована (3–9)",
        description="Збалансована шкала із симетричними уточненнями переваги",
        options=options,
    )


def _power_scale() -> ScaleDefinition:
    base_values = {
        3: 6.3,
        4: 7.1,
        5: 7.6,
        6: 8.1,
        7: 8.6,
        8: 9.0,
        9: 9.4,
    }
    options = tuple(
        ScaleOption(f"{k} – перша переважає", v) for k, v in base_values.items()
    ) + (
        ScaleOption("Рівнозначні", 5.5),
    ) + tuple(
        ScaleOption(f"{k} – друга переважає", 11 - v) for k, v in base_values.items()
    )
    return ScaleDefinition(
        key="power",
        name="Потенційна (3–9)",
        description="Потенційна шкала для уточнення переваг",
        options=options,
    )


def _ma_zheng_scale() -> ScaleDefinition:
    values = {
        "Незначна перевага": 6.2,
        "Помірна перевага": 7.0,
        "Суттєва перевага": 7.8,
        "Велика перевага": 8.6,
        "Надзвичайна перевага": 9.4,
    }
    options = tuple(
        ScaleOption(f"{label} першої", value) for label, value in values.items()
    ) + (
        ScaleOption("Рівнозначні", 5.5),
    ) + tuple(
        ScaleOption(f"{label} другої", 11 - value) for label, value in values.items()
    )
    return ScaleDefinition(
        key="ma_zheng",
        name="Ма – Чжен",
        description="Шкала Ма – Чжен для експертних оцінок",
        options=options,
    )


def _donegan_dodd_scale() -> ScaleDefinition:
    values = {
        "Слабка перевага": 6.4,
        "Легка перевага": 7.1,
        "Виражена перевага": 7.9,
        "Сильна перевага": 8.7,
        "Абсолютна перевага": 9.5,
    }
    options = tuple(
        ScaleOption(f"{label} першої", value) for label, value in values.items()
    ) + (
        ScaleOption("Рівнозначні", 5.5),
    ) + tuple(
        ScaleOption(f"{label} другої", 11 - value) for label, value in values.items()
    )
    return ScaleDefinition(
        key="donegan_dodd",
        name="Донаган – Додд – МакМастер",
        description="Шкала Донаган – Додд – МакМастер для уточнення переваг",
        options=options,
    )


AVAILABLE_SCALES: Dict[str, ScaleDefinition] = {
    scale.key: scale
    for scale in (
        _ordinal_scale(),
        _integer_scale(),
        _balanced_scale(),
        _power_scale(),
        _ma_zheng_scale(),
        _donegan_dodd_scale(),
    )
}


def ratio_from_cardinal(cardinal_value: float) -> float:
    """Перетворює значення у діапазоні 1.5–9.5 на відношення переваги."""
    midpoint = 5.5
    if cardinal_value == midpoint:
        return 1.0
    return cardinal_value / (11.0 - cardinal_value)

