from datetime import datetime
from enum import IntEnum, StrEnum
from src.api.constants import DATE_TIME_FORMAT, FROM_TIME, TO_TIME
from fastapi import Depends, Query


class RiskAccidentSource(StrEnum):
    """Класс случаев риска."""

    ROUTER = "Риск инцидент: сбой в работе рутера."
    EQUIPMENT = "Риск инцидент: отказ оборудования."
    BROKER = "Риск инцидент: на стороне брокер."
    PO = "Риск инцидент: ПО."
    PROVAIDER = "Риск инцидент: сбой на стороне провайдер."



class TechProcess(IntEnum):
    """Класс тех. процессов."""

    DU_25 = 25
    SPEC_DEP_26 = 26
    CLIENTS_27 = 27


class Item():  # TODO Использовать класс в эндпоинте POST Suspension вместо параметров функции
    "Класс данных для фиксации случая простоя из формы."
    def __init__(
            self, datetime_start, datetime_finish, risk_accident, tech_process, description,
            implementing_measures, suspension_service
    ):
        self.datetime_start: datetime = Query(..., example=FROM_TIME)
        self.datetime_finish: datetime = Query(..., example=TO_TIME)
        self.risk_accident: RiskAccidentSource
        self.tech_process: TechProcess
        self.description: str = Query(..., max_length=256, example="Кратковременный сбой в работе оборудования.")
        self.implementing_measures: str = Query(..., max_length=256, example="Перезагрузка оборудования.")
