"""src/api/constants.py"""
from datetime import datetime, timedelta, timezone

from src.settings import settings

DATE_PATTERN = r"(\d{4}-\d{2}-\d{2})"
DATE_PATTERN_FORM = "^([0-2][1-9]|3[0-2])-(0[1-9]|1[0-2])-(202[4-9]|20[3-9][0-9])$"  # 01-01-2024
DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
DATE_FORMAT = "%d-%m-%Y"
DATE_TODAY_FORMAT = "%Y-%m-%d"
DISPLAY_TIME = 60 * 24
FILE_DATETIME_FORMAT = "%d-%m-%Y_%H%M%S"

# Таблица перевода
TRANSLATION_TABLE = str.maketrans("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "abvgdeezzijklmnoprstufhccss!y!eui")

TZINFO = timezone(timedelta(hours=settings.TIMEZONE_OFFSET))
ANALYTIC_FROM_TIME = (datetime.now(TZINFO) - timedelta(days=1)).strftime(DATE_TIME_FORMAT)
ANALYTIC_TO_TIME = (datetime.now(TZINFO)).strftime(DATE_TIME_FORMAT)
CREATE_SUSPENSION_FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).strftime(DATE_TIME_FORMAT)
CREATE_SUSPENSION_TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).strftime(DATE_TIME_FORMAT)
CREATE_TASK_START = (datetime.now(TZINFO)).strftime(DATE_FORMAT)
CREATE_TASK_DEADLINE = (datetime.now(TZINFO) + timedelta(days=7)).strftime(DATE_FORMAT)
FILE_NAME_SAVE_FORMAT = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)
FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now(TZINFO) - timedelta(days=1)).isoformat(timespec='minutes')
TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = (datetime.now(TZINFO) - timedelta(minutes=0)).isoformat(timespec='minutes')


# endpoints
ANALYTICS = "/analytics"
DOWNLOAD_FILES = "/download_files"
GET_ALL_ROUTE = "/"
GET_FILES = "/get_files"
GET_OPENED_ROUTE = "/opened"
FILES = "Files"
FILE_ID = "/{file_id}"
LOGIN = "api/auth/jwt/login"
ME_TODO = "/my_tasks_todo"
MY_TASKS = "/my_tasks_ordered"
MY_SUSPENSIONS = "/my_suspensions"
SUSPENSION_ID = "/{suspension_id}"
TASKS_GET = "Tasks GET"
TASK_ID = "/{task_id}"
TASKS_POST = "Tasks POST"
TASKS_POST_BY_FORM = "/form"

# auth
IS_REGISTERED = " is registered."


# files_alias
GET_FILE_BY_ID = "Получить файл по id."
CHOICE_FORMAT = "Формат представления"
FILE_SIZE_ENCODE = "utf-8"
FILE_SIZE_IN = 1000  # in kb
FILE_SIZE_VOLUME = " kb."
FILES_UPLOADED = "Загруженные файлы"
FILES_WRITTEN_DB = "Файлы записанные в базу данных"
ROUND_FILE_SIZE = 1
SOME_ID = 1
SOME_NAME = "some_name"
SEARCH_FILES_BY_NAME = "Поиск файлов по имени"
SEARCH_FILES_BY_ID = "Поиск файлов по id файлов"

# files_descriptions
GET_SEVERAL_FILES = "Получить несколько файлов."
UPLOAD_FILES_BY_FORM = "Загрузка файлов из формы."


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
COPY_FILE_ERROR = "Ошибка при копировании файла."
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
ALREADY_EXISTS = " уже существует"
ALLOWED_FILE_SIZE_DOWNLOAD = ", допустимый размер: "
ALLOWED_FILE_TYPE_DOWNLOAD = " Допустимые типы: "
FILES_DOWNLOAD_ERROR = "Ошибка загрузки файлов и записи их в БД: "
FIlE_SIZE_EXCEEDED = " Превышен допустимый размер файла к загрузке - "
FILE_TYPE_DOWNLOAD_ALLOWED = " - данный тип файла не допустим для закгрузки!"
FILE_SEARCH_DOWNLOAD_OPTION = "Выберите тип поиска: по id или имени файла (не одновременно)!"
FUNCTION_STARTS = "Запущенна функция: "
MISS_LOGGING_UPDATES = "Следующие Updates не были пойманы ни одним из обработчиков"
NOT_FOUND = " - not found!"
ONLY_AUTHOR = "Только автор и админ могут редактировать!"
PASSWORD_LENGTH_WARNING = "Password should be at least 6 characters!"
PASSWORD_EMAIL_WARNING = "Password should not contain e-mail!"

# register_connection_errors: check Internet access info
FAILED_GET_URL = "Failed_get_url."
FIRST_COUNTER = "First_time_counter."
INFO_CONNECTIONS = "Info_connections"
SUPPOSE_OK = "Didn't try, suppose OK!"
SUSPENSION_CREATED = "Suspension_created."
SUSPENSION_DB_LOADED = "Suspension_loaded_in_db."
TIME_COUNTER = "Time_counter."
TIME_INFO = "time"
URL_CONNECTION_ERROR = "ConnectionError"
WITH_ID = " with id - "
