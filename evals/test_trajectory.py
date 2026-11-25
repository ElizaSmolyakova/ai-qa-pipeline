import json
from pathlib import Path


def test_last_pipeline_run_trajectory():
    trace_file = Path("trace_log.json")
    assert trace_file.exists(), "Файл trace_log.json не найден! Сначала запусти пайплайн: python -m src.code_generator"

    events = json.loads(trace_file.read_text(encoding="utf-8"))
    steps = [e["step_name"] for e in events]
    tools = [e["tool"] for e in events]

    print(f"\n🧭 Траектория последнего прогона: {steps}")
    print(f"🛠️ Инструменты: {tools}")

    # 1. Проверка строгой последовательности шагов
    assert steps == ["retrieval", "test_design", "code_generation"], (
        f"Нарушена траектория! Ожидалось ['retrieval', 'test_design', 'code_generation'], получено: {steps}"
    )

    # 2. Проверка бюджета вызовов LLM
    llm_calls = [e for e in events if e["tool"] == "ollama_llm"]
    assert len(llm_calls) == 2, f"Ожидалось ровно 2 вызова LLM, сделано: {len(llm_calls)}"
