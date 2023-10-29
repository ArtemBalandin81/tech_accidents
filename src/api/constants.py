from datetime import datetime, timedelta, timezone
from src.settings import settings

SLEEP_TEST_CONNECTION: int = 20
CONNECTION_TEST_URL = "https://www.agidel-am.ru"
DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"

TZINFO = timezone(timedelta(hours=settings.TIMEZONE_OFFSET))

FROM_TIME = (datetime.now(TZINFO) - timedelta(minutes=5)).isoformat(timespec='minutes')
#FROM_TIME = (datetime.utcnow() - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now(TZINFO) - timedelta(days=1)).isoformat(timespec='minutes')

TO_TIME = (datetime.now(TZINFO) - timedelta(minutes=1)).isoformat(timespec='minutes')
#TO_TIME = (datetime.utcnow() - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = (datetime.now(TZINFO) - timedelta(minutes=0)).isoformat(timespec='minutes')
