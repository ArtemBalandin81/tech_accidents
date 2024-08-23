"""src/api/constants.py"""
from datetime import datetime, timedelta, timezone

from src.settings import settings

DATE_PATTERN = r"(\d{4}-\d{2}-\d{2})"
DATE_PATTERN_FORM = "^([0-2][1-9]|3[0-2])-(0[1-9]|1[0-2])-(202[4-9]|20[3-9][0-9])$"  # 01-01-2024
DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
DATE_FORMAT = "%d-%m-%Y"
DATE_TODAY_FORMAT = "%Y-%m-%d"
FILE_DATETIME_FORMAT = "%d-%m-%Y_%H%M%S"

# Таблица перевода
TRANSLATION_TABLE = str.maketrans("абвгдеёжзийклмнопрстуфхцчшщъыьэюя", "abvgdeezzijklmnoprstufhccss!y!eui")

TZINFO = timezone(timedelta(hours=settings.TIMEZONE_OFFSET))
ANALYTIC_FROM_TIME = (datetime.now(TZINFO) - timedelta(days=settings.ANALYTICS_INTERVAL)).strftime(DATE_TIME_FORMAT)
ANALYTIC_TO_TIME = (datetime.now(TZINFO)).strftime(DATE_TIME_FORMAT)
CREATE_SUSPENSION_FROM_TIME = (
    (datetime.now(TZINFO) - timedelta(minutes=settings.CREATE_FROM_TIME)).strftime(DATE_TIME_FORMAT)
)
CREATE_SUSPENSION_TO_TIME = (
    (datetime.now(TZINFO) - timedelta(minutes=settings.CREATE_TO_TIME)).strftime(DATE_TIME_FORMAT)
)
CREATE_TASK_START = (datetime.now(TZINFO)).strftime(DATE_FORMAT)
CREATE_TASK_DEADLINE = (datetime.now(TZINFO) + timedelta(days=settings.DEFAULT_TASK_DEADLINE)).strftime(DATE_FORMAT)
FILE_NAME_SAVE_FORMAT = (datetime.now(TZINFO)).strftime(FILE_DATETIME_FORMAT)
FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now(TZINFO) - timedelta(days=1)).isoformat(timespec='minutes')
TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = datetime.now(TZINFO).isoformat(timespec='minutes')

# forms settings
FILE_NAME_LENGTH = 128
TASK_DESCRIPTION_LENGTH = 512
TASK_NAME_LENGTH = 128
SUSPENSION_DESCRIPTION_LENGTH = 256
SUSPENSION_IMPLEMENTING_MEASURES = 512

# endpoints files & services & users
DOWNLOAD_FILES = "/download_files"
FILE_ID = "/{file_id}"
GET_FILES = "/get_files"
GET_FILES_UNUSED = "/get_files_unused"

LOGIN = "api/auth/jwt/login"

# endpoints services
GET_TEST_URL = "/test_url"
DB_BACKUP = "/db_backup"

# endpoints suspensions
ADD_FILES_TO_SUSPENSION = "/add_files_to_suspension"
ANALYTICS = "/analytics"
MY_SUSPENSIONS = "/my_suspensions"
POST_SUSPENSION_FORM = "/post_suspension_form"
POST_SUSPENSION_FILES_FORM = "/post_suspension_with_files_form"
SUSPENSION_ID = "/{suspension_id}"

# endpoints tasks
ADD_FILES_TO_TASK = "/add_files_to_task"
GET_OPENED_ROUTE = "/opened"
MAIN_ROUTE = "/"
ME_TODO = "/my_tasks_todo"
MY_TASKS = "/my_tasks_ordered"
POST_TASK_FORM = "/post_task_form"
POST_TASK_FILES_FORM = "/post_task_with_files_form"
TASK_ID = "/{task_id}"

# endpoints TAGS
ANALYTICS_SUSPENSION = "Аналитика случаев простоя"
FILES = "Файлы: загрузка, получение, удаление"  # кириллица в swagger
TASKS_POST = "Задачи: назначить задачу"  # кириллица в swagger
TASKS_GET = "Задачи: посмотреть задачи"  # кириллица в swagger
SUSPENSIONS_POST = "Случаи простоя: внесение, редактирование, удаление"  # кириллица в swagger
SUSPENSIONS_GET = "Случаи простоя: получение информации"  # кириллица в swagger

# auth
IS_REGISTERED = " is registered."

# files_alias
ARRAYS_DIFFERENCE = "Бесхозные файлы (ids): "
CHOICE_FORMAT = "Формат представления: "
FILES_IDS_DELETED = "ids удаленных файлов: "
FILES_IDS_INTERSECTION = "Общие ids множеств: "
FILES_IDS_UNUSED_IN_DB = "ids бесхозных файлов в БД: "
FILES_IDS_WRITTEN_DB = "id файлов, записанных в базу данных"
FILES_IN_FOLDER = "Файлы в каталоге файлов: "
FILES_UNLINK = "Удалить все прикрепленные файлы"
FILES_UNUSED_IN_DB = "Бесхозные файлы в БД: "
FILES_UNUSED_IN_DB_REMOVED = "Из БД удалены бесхозные файлы: "
FILES_RECEIVED = "Files_received: "
FILES_SET_TO = "Привязанные файлы: "
FILE_SIZE_ENCODE = "utf-8"
FILE_SIZE_IN = 1000  # in kb
FILE_SIZE_VOLUME = " kb."
FILES_UNUSED_IN_FOLDER = "Бесхозные файлы в каталоге файлов: "
FILES_UNUSED_IN_FOLDER_REMOVED = "Из каталога удалены бесхозные файлы: "
FILES_UPLOADED = "Загруженные файлы"
FILES_WRITTEN_DB = "Файлы записанные в базу данных"
GET_FILE_BY_ID = "Получить файл по id: "
ROUND_FILE_SIZE = 1
SOME_NAME = "dd-mm-2024"  # "could_find_names_and_digits_eng"
SEARCH_FILES_BY_NAME = "Поиск файлов по имени: "
SEARCH_FILES_BY_ID = "Поиск файлов по id файлов: "

# files_descriptions
FILES_ATTACHED_TO_SUSPENSION = ". К случаю простоя добавлены следующие файлы: "
FILES_ATTACHED_TO_TASK = ". К задаче добавлены следующие файлы: "
FILE_DELETE = "Удалить файл (только админ)."
FILE_NAME = "Имя файла."
GET_SEVERAL_FILES = "Получить несколько файлов."
MANAGE_FILES_UNUSED = "Управление бесхозными файлами (только админ)."
UPLOAD_FILES_BY_FORM = "Загрузка файлов из формы: "

# suspensions_alias
ANALYTICS_START = "Начало периода: "
ANALYTICS_FINISH = "Окончание периода: "
CREATED = "Дата создания"
IMPLEMENTING_MEASURES = "Предпринятые действия"
MINS_TOTAL = "Сумма простоев в периоде (мин.)"
RISK_ACCIDENT = "Риск-инцидент"
RISK_ACCIDENT_SOURCE = "Источник угроз"
SUSPENSION = "Простой: "
SUSPENSION_CREATE_FORM = "Фиксация простоя из формы с возможностью загрузки 1 файла."
SUSPENSION_FILES_CREATE_FORM = "Фиксация простоя из формы с обязательной загрузкой нескольких файлов."
SUSPENSION_DELETED = "Случай простоя удален: "
SUSPENSION_DESCRIPTION = "Описание простоя: "
SUSPENSION_DURATION = "Простой (мин)"
SUSPENSION_DURATION_RESPONSE = 60  # in mins
SUSPENSION_FINISH = "Окончание простоя"
SUSPENSION_LAST_ID = "ID крайнего простоя в БД"
SUSPENSION_LAST_TIME = "Крайний простой в БД"
SUSPENSION_MAX_TIME = "Максимальный простой в периоде (в мин.)"
SUSPENSION_PATCH_FORM = "Редактирование случая простоя из формы: "
SUSPENSION_START = "Начало простоя"
SUSPENSION_TOTAl = "Количество простоев в периоде"
TECH_PROCESS = "Тех-процесс: "
UPDATED = "Дата обновления"
USER_MAIL = "Почта пользователя"
USER_ID = "id пользователя"

# suspensions_descriptions
ANALYTICS_SUSPENSION_LIST = "Аналитика случаев простоя."
SET_FILES_LIST_TO_SUSPENSION = "Прикрепляет к случаю простоя список файлов."
SUSPENSION_DELETE = "Удалить случай простоя (только админ)."
SUSPENSION_LIST = "Список всех случаев простоя."
SUSPENSION_LIST_CURRENT_USER = "Список случаев простоя текущего пользователя."

# create_suspension
CREATE_DESCRIPTION = "Кратковременный сбой в работе оборудования."
ROUTER_ERROR = "Риск инцидент: сбой в работе рутера."
INTERNET_ERROR = "Сбой подключения к интернет."
MEASURES = "Перезагрузка оборудования."

# tasks_alias
IS_ARCHIVED = "Задача выполнена"
TASK = "Задача: "
TASK_CREATE_FORM = "Постановка задачи из формы с возможностью загрузки 1 файла."
TASK_DELETED = "Задача удалена: "
TASK_FILES_CREATE_FORM = "Постановка задачи из формы с обязательной загрузкой нескольких файлов."
TASK_DURATION = "Дней на задачу"
TASK_DURATION_RESPONSE = (60 * 60 * 24)  # in days
TASK_DESCRIPTION = "Описание задачи: "
TASK_EXECUTOR = "Исполнитель задачи: "
TASK_EXECUTOR_MAIL = "Почта исполнителя"
TASK_EXECUTOR_MAIL_NOT_FROM_ENUM = "Почта исполнителя не из списка"

TASK_FINISH = "Дедлайн по задаче: "
TASK_PATCH_FORM = "Редактирование задачи из формы: "
TASK_START = "Дата постановки задачи"
TASK_USER_ID = "Постановщик задачи"

# tasks_descriptions
SET_FILES_LIST_TO_TASK = "Присваивает задаче список файлов."
TASK_DELETE = "Удалить задачу (только админ)."
TASK_LIST = "Список всех задач."
TASK_OPENED_LIST = "Список невыполненных задач."
MY_TASKS_LIST = "ЗАДАЧИ ВЫДАННЫЕ: список задач, выданных пользователем."
ME_TODO_LIST = "ЗАДАЧИ ПОЛУЧЕННЫЕ: список задач, выданных пользователю."

# warnings
SPACE = " "
ALREADY_EXISTS = " уже существует"
ALLOWED_FILE_SIZE_DOWNLOAD = ", допустимый размер: "
ALLOWED_FILE_TYPE_DOWNLOAD = " Допустимые типы: "
INACTIVE_USER_WARNING = {"description": "Missing token or inactive user."}
FILES_DOWNLOAD_ERROR = "Ошибка загрузки файлов и записи их в БД: "
FILES_REMOVE_FORBIDDEN = "Запрещено удалять привязанные файлы: "
FIlE_SIZE_EXCEEDED = " Превышен допустимый размер файла к загрузке - "
FILE_TYPE_DOWNLOAD_NOT_ALLOWED = " - данный тип файла не допустим для закгрузки!"
FILE_SEARCH_DOWNLOAD_OPTION = "Выберите тип поиска: по id или имени файла (не одновременно)!"
FUNCTION_STARTS = "Запущенна функция: "
MISS_LOGGING_UPDATES = "Следующие Updates не были пойманы ни одним из обработчиков"
NO_USER = "Check USER is not NONE!"
NOT_FOUND = " - not found!"
NOT_SUPER_USER_WARNING = {"description": "Not a superuser."}
ONLY_AUTHOR = "Только автор и админ могут редактировать!"
SAME_NAMES = " загружается один файл дважды: "
START_FINISH_TIME = {"description": "Check start_time > finish_time"}
SUSPENSION_FILES_MISMATCH = ". Несоответствие в таблицах SuspensionFiles и Files: "
TASKS_FILES_MISMATCH = ". Несоответствие в таблицах TasksFiles и Files: "
TASKS_FILES_REMOVE_AND_SET = "Запрещено одновременно удалять и добавлять файлы. Выберите одно из действий!"
#USER_NOT_PROVIDED = "Пользователь не предоставлен: делаю запрос пользователя в БД "
USER_NOT_PROVIDED = "User is not provided: making a request of user in db "
PASSWORD_LENGTH_WARNING = "Password should be at least 6 characters!"
PASSWORD_EMAIL_WARNING = "Password should not contain e-mail!"

# register_connection_errors: check Internet access info
GET_URL_DESCRIPTION = "Проверка доступа к сайту."
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

# db_backups
COPY_FILE_ERROR = "Ошибка при копировании файла."
DB_BACKUP_DESCRIPTION = "Бэкап БД."
DELETED_OK = " успешно удален(а)."
DIR_CREATED = "Создан каталог."
DIR_CREATED_ERROR = "Ошибка создания каталога."
FILE_EXISTS_ERROR = "Файл уже существует."
FILE_SAVED = "Файл успешно скопирован."
