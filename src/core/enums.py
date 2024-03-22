import json
from enum import Enum, IntEnum, StrEnum
from src.api.constants import EMPLOYEES
from src.settings import settings

# Executor = Enum('Executor', EMPLOYEES)
Executor = Enum('Executor', json.loads(settings.STAFF))
"""Enum-класс для исполнителей задач для подстановки в форму задач в api."""


class RiskAccidentSource(StrEnum):  # todo занести в константы и заменить как Executor
    """Класс случаев риска."""

    ROUTER = "Риск инцидент: сбой в работе рутера."
    EQUIPMENT = "Риск инцидент: отказ оборудования."
    BROKER = "Риск инцидент: на стороне брокер."
    PO = "Риск инцидент: ПО."
    PROVAIDER = "Риск инцидент: сбой на стороне провайдер."


class TechProcess(IntEnum):  # todo занести в константы и заменить как Executor
    """Класс тех. процессов."""

    DU_25 = 25
    SPEC_DEP_26 = 26
    CLIENTS_27 = 27
