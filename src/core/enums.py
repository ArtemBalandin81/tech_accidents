"""src/core/enums.py"""
import json
from enum import StrEnum

from src.settings import settings

ChoiceDownloadFiles = StrEnum('ChoiceDownloadFiles', json.loads(settings.CHOICE_DOWNLOAD_FILES))
"""Enum-класс для кнопки выбора загрузки json (False) или файлов (True)."""

Executor = StrEnum('Executor', json.loads(settings.STAFF))
"""Enum-класс для исполнителей задач для подстановки в форму задач в api."""

TechProcess = StrEnum('TechProcess', json.loads(settings.TECH_PROCESS))
"""Enum-класс используемых тех.процессов."""

RiskAccidentSource = StrEnum('RiskAccidentSource', json.loads(settings.RISK_SOURCE))
"""Enum-класс используемых угроз."""


