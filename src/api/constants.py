from datetime import datetime, timedelta, timezone
from src.settings import settings

DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
DISPLAY_TIME = 60 * 24
CONNECTION_TEST_URL_AGI = "https://www.agidel-am.ru"
CONNECTION_TEST_URL_YA = "https://www.ya.ru"
SLEEP_TEST_CONNECTION: int = 20

TZINFO = timezone(timedelta(hours=settings.TIMEZONE_OFFSET))

FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now(TZINFO) - timedelta(days=1)).isoformat(timespec='minutes')

TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = (datetime.now(TZINFO) - timedelta(minutes=0)).isoformat(timespec='minutes')
