from datetime import datetime, timedelta, timezone
from src.settings import settings

DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
DISPLAY_TIME = 60 * 24
CONNECTION_TEST_URL_AGI = "https://www.agidel-am.ru"
CONNECTION_TEST_URL_YA = "https://www.ya.ru"
SLEEP_TEST_CONNECTION: int = 20

TZINFO = timezone(timedelta(hours=settings.TIMEZONE_OFFSET))
ANALYTIC_FROM_TIME = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
ANALYTIC_TO_TIME = (datetime.now(TZINFO)).strftime(DATE_TIME_FORMAT)
CREATE_SUSPENSION_FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).strftime(DATE_TIME_FORMAT)
CREATE_SUSPENSION_TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).strftime(DATE_TIME_FORMAT)
FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now(TZINFO) - timedelta(days=1)).isoformat(timespec='minutes')
TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = (datetime.now(TZINFO) - timedelta(minutes=0)).isoformat(timespec='minutes')

# create_suspension
CREATE_DESCRIPTION = "Кратковременный сбой в работе оборудования."
ROUTER_ERROR = "Риск инцидент: сбой в работе рутера."
INTERNET_ERROR = "Сбой подключения к интернет."
MEASURES = "Перезагрузка оборудования."

# alias
CREATED = "Дата создания"
IMPLEMENTING_MEASURES = "Предпринятые действия"
MINS_TOTAL = "Минут итого"
RISK_ACCIDENT = "Риск-инцидент"
SUSPENSION_DESCRIPTION = "Описание простоя"
SUSPENSION_FINISH = "Окончание простоя"
SUSPENSION_LAST_ID = "ID последнего простоя"
SUSPENSION_LAST_TIME = "Время последнего простоя"
SUSPENSION_MAX_TIME = "Максимальный простой мин."
SUSPENSION_START = "Начало простоя"
SUSPENSION_TOTAl = "Простоев итого"
TECH_PROCESS = "Тех-процесс"
UPDATED = "Дата обновления"
USER_MAIL = "Почта пользователя"
USER_ID = "id пользователя"
