from fastapi import APIRouter
from enum import IntEnum, StrEnum
from typing import Optional
test_router = APIRouter()


class RiskAccident(StrEnum):
    """Класс случаев риска"""

    EQUIPMENT = 'Риск инцидент железо'
    PO = 'Риск инцидент ПО'
    PROVAIDER = 'Риск инцидент провайдер'


class TechProcess(IntEnum):
    """Класс тех процессов"""

    DU = 25
    SPEC_DEP = 26
    CLIENTS = 27


@test_router.get('/{title}')
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
