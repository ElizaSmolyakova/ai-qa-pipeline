import pytest
from src.ingest import get_collection, ingest_specs


@pytest.fixture(scope="module", autouse=True)
def ensure_db_populated():
    """Не трогает существующую базу; наполняет только если она пустая (в чистом CI)."""
    collection = get_collection()
    if collection.count() == 0:
        ingest_specs("specs")


@pytest.mark.parametrize(
    "query, expected_domain",
    [
        ("Что будет, если юзер введет неправильный пароль 5 раз?", "payments"),
        ("Какой статус вернется при оплате заказа с отрицательной суммой?", "payments"),
        ("Сколько минут действует токен доступа?", "payments"),
    ],
)
def test_vector_search_finds_correct_domain(query: str, expected_domain: str):
    """Проверяем, что векторный поиск находит требование из правильного функционального домена."""
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=1)
    meta = results["metadatas"]
    assert meta[0][0].get("domain") == expected_domain
