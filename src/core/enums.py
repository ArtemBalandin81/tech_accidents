import json
from enum import Enum, IntEnum, StrEnum
from src.settings import settings


Executor = StrEnum('Executor', json.loads(settings.STAFF))
"""Enum-класс для исполнителей задач для подстановки в форму задач в api."""


TechProcess = StrEnum('TechProcess', json.loads(settings.TECH_PROCESS))
"""Enum-класс используемых тех.процессов."""


RiskAccidentSource = StrEnum('TechProcess', json.loads(settings.RISK_SOURCE))
"""Enum-класс используемых угроз."""


# class RiskAccidentSource(StrEnum):
#     """Класс случаев риска."""
#
#     ROUTER = "Риск инцидент: сбой в работе рутера."
#     EQUIPMENT = "Риск инцидент: отказ оборудования."
#     BROKER = "Риск инцидент: на стороне брокер."
#     PO = "Риск инцидент: ПО."
#     PROVAIDER = "Риск инцидент: сбой на стороне провайдер."


# class TechProcess(IntEnum):
#     """Класс тех. процессов."""
#
#     DU_25 = 25
#     SPEC_DEP_26 = 26
#     CLIENTS_27 = 27
