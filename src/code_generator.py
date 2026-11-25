import ast
import re
import subprocess
import time
from pathlib import Path
from openai import OpenAI
from src.generator import generate_test_suite
from src.schemas import GeneratedCode, TestSuite
from src.telemetry.tracer import tracer
from src.skills_loader import load_skill

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


def run_pytest_gate(file_path: Path, suite: TestSuite) -> tuple[bool, str]:
    """Quality Gate 2: 5 жёстких проверок (синтаксис, античитинг, сверка кодов, Testcontainers)."""
    code = file_path.read_text(encoding="utf-8")

    # Замок 1: Валидный синтаксис Python
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
     return False, f"SyntaxError: {e}\nНачало файла: {code[:120]!r}"

    # Замок 2: Запрет хардкода URL
    if "example.com" in code or "localhost:8000" in code:
        return False, "Нарушение: найден хардкод URL (example.com или localhost:8000). Используй только фикстуру base_url!"

    # Замок 3: Сохранение количества тестов и запрет на пустышки
    test_funcs = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    if len(test_funcs) < len(suite.cases):
        return False, f"Жульничество: сценариев было {len(suite.cases)}, а тестов в коде только {len(test_funcs)}. Не удаляй тесты!"

    for func in test_funcs:
        func_src = ast.get_source_segment(code, func) or ""
        if "requests." not in func_src:
            return False, f"В тесте {func.name} нет реального HTTP-запроса через requests!"
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(func))
        if not has_assert or "assert True" in func_src:
            return False, f"В тесте {func.name} отсутствует осмысленный assert!"

    # Замок 4: Все ожидаемые статус-коды из сценариев обязаны остаться в коде
    expected_codes = {str(case.expected_status) for case in suite.cases}
    missing_codes = [c for c in expected_codes if c not in code]
    if missing_codes:
        return False, f"Из кода пропали ожидаемые статус-коды из сценариев: {missing_codes}. Верни их в assert!"

    # Замок 5: Живой прогон против Testcontainers (Docker)
    result = subprocess.run(
        ["pytest", str(file_path), "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return True, "OK"
    return False, result.stdout[-1500:]


def generate_pytest_with_healing(
    suite: TestSuite, output_dir: str = "generated_tests", max_retries: int = 3
) -> Path:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / "test_pay.py"

    messages = [
        {"role": "system", "content": load_skill("pytest_codegen")},
        {
            "role": "user",
            "content": f"Сгенерируй файл test_pay.py по этим сценариям:\n{suite.model_dump_json(indent=2)}",
        },
    ]

    for attempt in range(1, max_retries + 1):
        print(f"\n🔄 [Контур 2] Попытка генерации кода #{attempt} из {max_retries}...")
        t_start = time.time()

        response = client.chat.completions.create(
            model="qwen2.5-coder:3b",
            temperature=0.0,
            messages=messages,
        )
        raw_code = response.choices[0].message.content.strip()
        match = re.search(r"```(?:python)?\n(.*?)```", raw_code, re.DOTALL)
        if match:
            raw_code = match.group(1).strip()
        file_path.write_text(raw_code, encoding="utf-8")

        passed, feedback = run_pytest_gate(file_path, suite)
        tracer.log(
            f"code_generation_attempt_{attempt}",
            "ollama_llm",
            {"passed": passed, "filename": file_path.name},
            t_start,
        )

        if passed:
            print(f"✅ [Контур 2] Успех! Все 5 замков и Testcontainers пройдены с попытки #{attempt}!")
            return file_path

        print(f"❌ Попытка #{attempt} не прошла проверку:\n{feedback}\nПередаю ошибку на самоисправление...")
        messages.append({"role": "assistant", "content": raw_code})
        messages.append(
            {
                "role": "user",
                "content": f"Код не прошёл проверку. Исправь ошибки по этому логу и верни полный исправленный файл:\n{feedback}",
            }
        )

    raise RuntimeError(f"Агент не смог добиться зелёных тестов за {max_retries} попытки.")


if __name__ == "__main__":
    tracer.clear()
    suite = generate_test_suite("Составь позитивные и негативные тесты для сервиса оплаты")
    generate_pytest_with_healing(suite)
