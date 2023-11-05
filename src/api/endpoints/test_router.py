"""src/api/endpoints/test_router.py"""
import requests

from datetime import datetime
from fastapi import APIRouter, Depends, Path, Query

from enum import IntEnum, StrEnum


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
