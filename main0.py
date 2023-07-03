# main.py

from fastapi import FastAPI
from enum import IntEnum, StrEnum
from typing import Optional

app = FastAPI()


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


@app.get('/{title}')
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


@app.get('/')
def read_root():
    return {'Hello': 'FastAPI'}

@app.get('/{name}')
def greetings(name: str):
    return {'Hello': name.title()}
