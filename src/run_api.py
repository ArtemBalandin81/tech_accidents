"""src/run_api.py"""
import requests
import uvicorn

from application import create_app
from datetime import datetime
#from services import test_connection
from src.api.constants import CONNECTION_TEST_URL

def test_connection(CONNECTION_TEST_URL: str = "https://www.agidel-am.ru"):  # TODO -> ???:
    """ Тестирует доступ к интернет и сохраняет случай простоя в случае отсутствия доступа."""
    status_code = requests.get(CONNECTION_TEST_URL).status_code
    print(f"test_connection: {status_code}")
    return {url: status_code, "time": datetime.now().isoformat(timespec='seconds')}

def start_api():
    app = create_app()
    uvicorn.run(app, host="localhost", port=8001)

if __name__ == "__main__":
    start_api()
