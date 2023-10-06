"""src/api/endpoints/test_router.py"""
import requests

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Path, Query
from typing import Optional

from enum import IntEnum, StrEnum

from src.api.services import SuspensionService

test_router = APIRouter()


class RiskAccident(StrEnum):
    """Класс случаев риска"""

    EQUIPMENT = "Риск инцидент железо"
    PO = "Риск инцидент ПО"
    PROVAIDER = "Риск инцидент провайдер"
    ROUTER = "Сбой доступа в интернет"


class TechProcess(IntEnum):
    """Класс тех процессов"""

    DU = 25
    SPEC_DEP = 26
    CLIENTS = 27


AUTO_FIX_USER: int = 2  #TODO user передаем определенный, автомат

@test_router.get("/test_get_url")
def test_get_url(
    *,  # чтобы определять любой порядок аргументов (именнованных и нет)
    url: str = Query(..., example="https://www.agidel-am.ru"),
) -> dict[str, int | str]:
    status_code = requests.get(url).status_code
    return {url: status_code, "time": datetime.now().isoformat(timespec='seconds')}

@test_router.get("/run_test_create_suspension")
async def run_test_create_suspension(
    suspension_service: SuspensionService = Depends(),
):  #TODO что отдает?
    suspension_object = {
        "datetime_start": datetime.now() - timedelta(minutes=5),
        "datetime_finish": datetime.now(),
        "risk_accident": "Риск инцидент: сбой в работе рутера.",
        "tech_process": 25,
        "description": "Кратковременный сбой доступа в Интернет.",
        "implementing_measures": "Перезагрузка оборудования.",
    }
    await suspension_service.actualize_object(suspension_id=None, in_object=suspension_object, user=AUTO_FIX_USER)


@test_router.get("/{title}")
def suspensions(
    *,  # чтобы определять любой порядок аргументов (именнованных и нет)
    title: str,
    description: Optional[str] = None,
    tech_process: TechProcess,
    risk_accident: RiskAccident,
    suspension: int,
    #is_damage: bool = False,
) -> dict[str, str]:
    result = ' '.join(
        [title, str(tech_process), str(risk_accident), str(suspension)]
    )
    result = result.title()
    if description is not None:
        result += ', ' + str(description)
    return {'Suspension': result}
