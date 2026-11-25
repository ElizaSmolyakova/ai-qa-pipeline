from pathlib import Path
from pydantic import BaseModel, Field
from src.generator import MODEL_NAME, client, generate_test_suite
import pytest
from src.skills_loader import load_skill



# Контракт для ответа "Судьи" (LLM-as-a-Judge)
class JudgeVerdict(BaseModel):
    score: int = Field(description="Оценка от 1 до 5, где 5 - идеально соответствует требованиям")
    reason: str = Field(description="Краткое объяснение оценки на русском")
    has_hallucinations: bool = Field(description="True, если модель выдумала факты, которых нет в требованиях")


@pytest.mark.llm
def test_generated_payment_cases_deterministic():
    """Уровень 1 и 2: Детерминированные проверки структуры, покрытия и отсутствия выдуманных URL"""
    suite = generate_test_suite("Составь позитивные и негативные тесты для сервиса оплаты")

    # 1. Проверяем, что тесты вообще сгенерировались
    assert len(suite.cases) >= 2, "Сгенерировано слишком мало тест-кейсов!"

    # 2. Проверяем, что есть и позитивный, и негативный сценарии
    has_positive = any(not c.is_negative for c in suite.cases)
    has_negative = any(c.is_negative for c in suite.cases)
    assert has_positive, "Не найден ни один позитивный тест-кейс"
    assert has_negative, "Не найден ни один негативный тест-кейс"

    # 3. Защита от галлюцинаций: все тесты должны бить в реальный эндпоинт из specs/payment.md
    for case in suite.cases:
        assert "/api/v1/pay" in case.endpoint, f"Галлюцинация! Выдуманный эндпоинт: {case.endpoint}"

    # 4. Проверяем покрытие ключевого требования: отрицательная сумма -> 400 Bad Request
    statuses = [c.expected_status for c in suite.cases]
    assert 400 in statuses, f"Не покрыт негативный кейс со статусом 400! Получены статусы: {statuses}"


@pytest.mark.llm
def test_generated_cases_llm_as_a_judge():
    """Уровень 3: Семантическая проверка через LLM-as-a-Judge (поиск галлюцинаций)"""
    spec_text = Path("specs/payment.md").read_text(encoding="utf-8")
    suite = generate_test_suite("Составь тесты для сервиса оплаты")

    # Форматируем сгенерированные тесты в читаемый текст для судьи
    cases_summary = "\n".join(
        f"- {c.title} | {c.endpoint} | Ожидаемый статус: {c.expected_status}"
        for c in suite.cases
    )

    judge_response = client.beta.chat.completions.parse(
        model=MODEL_NAME,
        messages=[
            {
                "role": "system",
                "content": load_skill("llm_judge"),
            },
            {
                "role": "user",
                "content": f"Исходные требования:\n{spec_text}\n\nСгенерированные тесты:\n{cases_summary}",
            },
        ],
        response_format=JudgeVerdict,
    )

    verdict = judge_response.choices[0].message.parsed
    print(f"\n⚖️ Вердикт судьи: {verdict.score}/5 | Галлюцинации: {verdict.has_hallucinations} | {verdict.reason}")

    assert not verdict.has_hallucinations, f"Судья нашел галлюцинации: {verdict.reason}"
    assert verdict.score >= 4, f"Низкое качество генерации ({verdict.score}/5): {verdict.reason}"
