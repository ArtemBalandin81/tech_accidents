from datetime import datetime, timedelta

CONNECTION_TEST_URL = "https://www.agidel-am.ru"
DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"

FROM_TIME = (datetime.now() - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now() - timedelta(days=1)).isoformat(timespec='minutes')
SLEEP_TEST_CONNECTION: int = 20
TIME_ZONE_SHIFT = 5
TO_TIME = (datetime.now() - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = (datetime.now() - timedelta(minutes=0)).isoformat(timespec='minutes')
