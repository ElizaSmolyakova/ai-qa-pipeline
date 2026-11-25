import pytest
from src.ingest import get_collection, ingest_specs


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    # Перед запуском тестов убеждаемся, что спеки загружены в базу
    ingest_specs("specs")


@pytest.mark.parametrize(
    "query, expected_file",
    [
        ("Что будет, если юзер введет неправильный пароль 5 раз?", "auth.md"),
        ("Какой статус вернется при оплате заказа с отрицательной суммой?", "payment.md"),
        ("Сколько минут действует токен доступа?", "auth.md"),
    ],
)
def test_vector_search_finds_correct_spec(query: str, expected_file: str):
    collection = get_collection()

    # Ищем 1 самый подходящий документ по смыслу
    results = collection.query(query_texts=[query], n_results=1)

    # Достаем метаданные первого найденного результата
    found_source = results["metadatas"][0][0]["source"]

    assert found_source == expected_file, (
        f"Ошибка поиска! На запрос '{query}' база вернула '{found_source}', "
        f"а ожидался файл '{expected_file}'."
    )
