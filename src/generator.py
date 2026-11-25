from openai import OpenAI
from src.ingest import get_collection
from src.schemas import TestSuite
import time
from src.telemetry.tracer import tracer
from src.skills_loader import load_skill

# Подключаемся к локальной Ollama — никуда в интернет данные не уходят
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)

# Укажи здесь имя модели, которое показала команда `ollama list`
MODEL_NAME = "qwen2.5-coder:3b"


def generate_test_suite(query: str) -> TestSuite:
    # 1. Ищем нужные требования в векторной базе
    collection = get_collection()
    if collection.count() == 0:
        ingest_specs("specs")
        collection = get_collection()

    t0 = time.time()
    results = collection.query(query_texts=[query], n_results=1)
    context = results["documents"][0][0]
    tracer.log("retrieval", "chromadb", {"query": query}, t0)

    # 2. Просим локальную модель сгенерировать тесты строго по Pydantic-схеме
    t1 = time.time()
    response = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
                        {
                "role": "system",
                "content": load_skill("test_designer"),
            },
        {
                "role": "user",
                "content": f"Требования:\n{context}\n\nЗадача: {query}",
            },
        ],
        response_format=TestSuite,
    )

    suite = response.choices[0].message.parsed
    tracer.log("test_design", "ollama_llm", {"cases_count": len(suite.cases)}, t1)
    return suite


if __name__ == "__main__":
    suite = generate_test_suite("Составь позитивные и негативные тесты для сервиса оплаты")
    for idx, case in enumerate(suite.cases, 1):
        print(f"{idx}. [{case.expected_status}] {case.title} | {case.endpoint} | Negative: {case.is_negative}")
