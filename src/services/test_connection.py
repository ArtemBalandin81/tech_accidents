import requests

from datetime import datetime

from src.api.constants import CONNECTION_TEST_URL


async def test_connection(CONNECTION_TEST_URL: str = "https://www.agidel-am.ru"):  # TODO -> ???:
    """ Тестирует доступ к интернет и сохраняет случай простоя в случае отсутствия доступа."""
    status_code = requests.get(CONNECTION_TEST_URL).status_code
    print(f"test_connection: {status_code}")
    return {url: status_code, "time": datetime.now().isoformat(timespec='seconds')}
