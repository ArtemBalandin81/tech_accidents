from datetime import datetime, timedelta, timezone
from src.settings import settings

DATE_PATTERN = r"(\d{4}-\d{2}-\d{2})"
DATE_PATTERN_FORM = "^([0-2][1-9]|3[0-2])-(0[1-9]|1[0-2])-(202[4-9]|20[3-9][0-9])$"  # 01-01-2024
DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
DATE_FORMAT = "%d-%m-%Y"
DATE_TODAY_FORMAT = "%Y-%m-%d"
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
ANALYTICS = "/analytics"
GET_ALL_ROUTE = "/"
GET_OPENED_ROUTE = "/opened"
ME_TODO = "/my_tasks_todo"
MY_TASKS = "/my_tasks_ordered"
MY_SUSPENSIONS = "/my_suspensions"
SUSPENSION_ID = "/{suspension_id}"
TASKS_GET = "Tasks GET"
TASK_ID = "/{task_id}"
TASKS_POST = "Tasks POST"
TASKS_POST_BY_FORM = "/form"

# suspensions_alias
CREATED = "Дата создания"
IMPLEMENTING_MEASURES = "Предпринятые действия"
MINS_TOTAL = "Минут итого"
RISK_ACCIDENT = "Риск-инцидент"
RISK_ACCIDENT_SOURCE = "Источник угроз"
SUSPENSION_DESCRIPTION = "Описание простоя"
SUSPENSION_DURATION = "Простой (мин)"
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
IS_ARCHIVED = "Задача выполнена"
TASK = "Задача"
TASK_CREATE_FORM = "Постановка задачи из формы."
TASK_DURATION = "Дней на задачу"
TASK_DESCRIPTION = "Описание задачи."
TASK_EXECUTOR = "Исполнитель задачи"
TASK_EXECUTOR_MAIL = "Почта исполнителя"
TASK_EXECUTOR_MAIL_NOT_FROM_ENUM = "Почта исполнителя не из списка"
TASK_FINISH = "Дедлайн по задаче"
TASK_PATCH_FORM = "Редактирование задачи из формы."
TASK_START = "Дата постановки задачи"
TASK_USER_ID = "Постановщик задачи"

# tasks_descriptions
TASK_DELETE = "Удалить задачу (только админ)."
TASK_LIST = "Список всех задач."
TASK_OPENED_LIST = "Список невыполненных задач."
MY_TASKS_LIST = "ЗАДАЧИ ВЫДАННЫЕ: список задач, выданных пользователем."
ME_TODO_LIST = "ЗАДАЧИ ПОЛУЧЕННЫЕ: список задач, выданных пользователю."

# warnings
ONLY_AUTHOR = "Только автор и админ могут редактировать!"  # todo в константы

# staff todo занести в .env
EMPLOYEES = {
    # "1": "another",
    "2": "user@example.com",
    "3": "true@example.com",
    "4": "true2@example.com",
    "5": "user5@example.com",
    "6": "test_user_ex@example.com",
    "7": "user54378@example.com"
}
