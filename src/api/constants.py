from datetime import datetime, timedelta

DATE_TIME_FORMAT = "%d-%m-%Y: %H:%M"
FROM_TIME = (datetime.now() - timedelta(minutes=5)).isoformat(timespec='minutes')
TO_TIME = (datetime.now() - timedelta(minutes=1)).isoformat(timespec='minutes')
