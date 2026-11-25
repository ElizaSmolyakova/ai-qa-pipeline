import ast
from pathlib import Path
from pydantic import BaseModel, Field
from src.generator import MODEL_NAME, client, generate_test_suite
from src.schemas import TestSuite
import time 
from src.telemetry.tracer import tracer


class GeneratedTestFile(BaseModel):
    filename: str = Field(description="Имя файла на английском, например test_payment_generated.py")
    python_code: str = Field(description="Чистый валидный код автотестов на pytest без markdown-оберток")


def generate_pytest_from_suite(suite: TestSuite, output_dir: str = "generated_tests") -> Path:
    # Явно передаём HTTP-метод и путь из каждого проверенного сценария
    scenarios_text = "\n".join(
        f"{i}. {c.title} | HTTP-метод: {c.http_method.upper()} | Путь: {c.endpoint} "
        f"| Негативный: {c.is_negative} | Ожидаемый код: {c.expected_status}"
        for i, c in enumerate(suite.cases, 1)
    )

    t2 = time.time()
    response = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": (
                    "Ты Senior SDET (QA Automation). Напиши автотесты на pytest строго по переданному списку "
                    "тест-сценариев (один тест-кейс = одна функция def test_...). "
                    "Используй тот HTTP-метод (requests.get, requests.post, requests.put, requests.delete), "
                    "который указан в поле 'HTTP-метод' каждого сценария. "
                    "Базовый URL сервера: http://localhost:8000 (например: http://localhost:8000/api/v1/pay). "
                    "В поле python_code пиши ТОЛЬКО чистый код Python, без ```python."
                ),
            },
            {
                "role": "user",
                "content": f"Автоматизируй следующие проверенные тест-сценарии:\n{scenarios_text}",
            },
        ],
        response_format=GeneratedTestFile,
    )
    # Превращаем проверенные тест-кейсы в аккуратный список для промпта
    scenarios_text = "\n".join(
        f"{i}. {c.title} | Метод и URL: {c.endpoint} | Негативный: {c.is_negative} | Ожидаемый код: {c.expected_status}"
        for i, c in enumerate(suite.cases, 1)
    )

    response = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
               "content": (
                    "Ты Senior SDET (QA Automation). Напиши автотесты на pytest строго по переданному списку "
                    "тест-сценариев (один тест-кейс = одна функция def test_...(base_url):). "
                    "Каждый тест ОБЯЗАН принимать параметр base_url и формировать адрес как f'{base_url}{endpoint}'. "
                    "Никогда не пиши example.com или hardcoded домены! "
                    "Используй тот HTTP-метод (requests.get, requests.post, requests.put, requests.delete), "
                    "который указан в поле 'HTTP-метод' каждого сценария. "
                    "В поле python_code пиши ТОЛЬКО чистый код Python, без ```python."
                ),
            },
            {
                "role": "user",
                "content": f"Автоматизируй следующие проверенные тест-сценарии:\n{scenarios_text}",
            },
        ],
        response_format=GeneratedTestFile,
    )

    generated = response.choices[0].message.parsed

    out_path = Path(output_dir)
    out_path.mkdir(exist_ok=True)
    filename = generated.filename
    if not filename.startswith("test_"):
        filename = f"test_{filename}"

    file_path = out_path / filename
    file_path.write_text(generated.python_code, encoding="utf-8")
    
    tracer.log("code_generation", "ollama_llm", {"filename": file_path.name}, t2)
    return file_path


def validate_python_syntax(file_path: Path) -> bool:
    code = file_path.read_text(encoding="utf-8")
    ast.parse(code)
    return True


if __name__ == "__main__":
    tracer.clear()
    # Шаг 1: Генерируем структурированные тест-кейсы из требований
    suite = generate_test_suite("Составь позитивные и негативные тесты для сервиса оплаты")
    print(f"📋 Сгенерировано сценариев: {len(suite.cases)}")

    # Шаг 2: Автоматизируем ИМЕННО ЭТИ сценарии в код pytest
    saved_file = generate_pytest_from_suite(suite)
    is_valid = validate_python_syntax(saved_file)

    print(f"✅ Автотесты сохранены в: {saved_file}")
    print(f"🔍 Проверка синтаксиса Python (AST): {'OK' if is_valid else 'FAIL'}")
