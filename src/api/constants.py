from datetime import datetime, timedelta

DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
TIME_ZONE_SHIFT = 5
FROM_TIME = (datetime.now() - timedelta(minutes=5)).isoformat(timespec='minutes')
FROM_TIME_NOW = (datetime.now() - timedelta(days=1)).isoformat(timespec='minutes')
TO_TIME = (datetime.now() - timedelta(minutes=1)).isoformat(timespec='minutes')
TO_TIME_PERIOD = (datetime.now() - timedelta(minutes=0)).isoformat(timespec='minutes')
