import time
import pytest
import requests
from testcontainers.core.container import DockerContainer


@pytest.fixture(scope="session")
def base_url():
    # Запускаем контейнер из нашего образа и пробрасываем порт 8000 наружу
    container = DockerContainer("payment-mock-api:latest").with_exposed_ports(8000)
    container.start()

    # Узнаем, какой случайный свободный порт на Mac выдал Docker
    host = container.get_container_host_ip()
    port = container.get_exposed_port(8000)
    url = f"http://{host}:{port}"

    # Ждем до 10 секунд, пока FastAPI внутри контейнера стартует
    for _ in range(20):
        try:
            if requests.get(f"{url}/health").status_code == 200:
                break
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)

    yield url  # Отдаем адрес контейнера во все сгенерированные тесты!

    # После прогона всех тестов контейнер автоматически удаляется
    container.stop()
