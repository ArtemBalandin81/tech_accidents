from datetime import datetime, timedelta, timezone
from src.settings import settings

DATE_PATTERN = r"(\d{4}-\d{2}-\d{2})"
DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
DATE_FORMAT = "%d-%m-%Y"
DISPLAY_TIME = 60 * 24
CONNECTION_TEST_URL_BASE = "https://www.agidel-am.ru"
CONNECTION_TEST_URL_YA = "https://www.ya.ru"

TZINFO = timezone(timedelta(hours=settings.TIMEZONE_OFFSET))
ANALYTIC_FROM_TIME = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
ANALYTIC_TO_TIME = (datetime.now(TZINFO)).strftime(DATE_TIME_FORMAT)
CREATE_SUSPENSION_FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).strftime(DATE_TIME_FORMAT)
CREATE_SUSPENSION_TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).strftime(DATE_TIME_FORMAT)
CREATE_TASK_START = (datetime.now(TZINFO)).strftime(DATE_FORMAT)
CREATE_TASK_DEADLINE = (datetime.now(TZINFO) + timedelta(days=7)).strftime(DATE_FORMAT)
FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now(TZINFO) - timedelta(days=1)).isoformat(timespec='minutes')
TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = (datetime.now(TZINFO) - timedelta(minutes=0)).isoformat(timespec='minutes')

# endpoints
GET_ALL_ROUTE = "/"
TASKS_GET = "Tasks GET"
TASK_ID = "/{task_id}"
TASKS_POST = "Tasks POST"
TASKS_POST_BY_FORM = "/form"

# suspensions_alias
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

# create_suspension
CREATE_DESCRIPTION = "Кратковременный сбой в работе оборудования."
ROUTER_ERROR = "Риск инцидент: сбой в работе рутера."
INTERNET_ERROR = "Сбой подключения к интернет."
MEASURES = "Перезагрузка оборудования."

# db_backups
COPY_FILE_ERROR ="Ошибка при копировании файла."
DELETED_OK = " успешно удален."
DIR_CREATED = "Создан каталог."
DIR_CREATED_ERROR = "Ошибка создания каталога."
FILE_EXISTS_ERROR = "Файл уже существует."
FILE_SAVED = "Файл успешно скопирован."


# tasks_alias
TASK = "Задача"
TASK_CREATE_FORM = "Постановка задачи из формы."
TASK_DESCRIPTION = "Описание задачи"
TASK_EXECUTOR = "Исполнитель задачи"
TASK_EXECUTOR_MAIL = "Почта исполнителя"
TASK_FINISH = "Дедлайн по задаче"
TASK_START = "Дата постановки задачи"
TASK_USER_ID = "Постановщик задачи"

# tasks_descriptions
TASK_DELETE = "Удалить задачу (только админ)."
TASK_LIST = "Список всех задач."
