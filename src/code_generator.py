import ast
import re, json
import subprocess
import time
from pathlib import Path
from openai import OpenAI
from src.generator import generate_test_suite
from src.schemas import GeneratedCode, TestSuite
from src.telemetry.tracer import tracer
from src.skills_loader import load_skill

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


def run_pytest_gate(file_path: Path, suite: TestSuite) -> tuple[str, str]:
    """Quality Gate 2: разделяет ошибки агента (AGENT_ERROR) и баги сервиса (SERVICE_MISMATCH)."""
    code = file_path.read_text(encoding="utf-8")

    # Замок 1: Валидный синтаксис Python
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return "AGENT_ERROR", f"SyntaxError в сгенерированном коде: {e}"

    # Замок 2: Запрет хардкода URL
    if "example.com" in code or "localhost:8000" in code:
        return "AGENT_ERROR", "Нарушение: найден хардкод URL (example.com или localhost:8000). Используй только фикстуру base_url!"

    # Замок 3: Сохранение количества тестов и запрет на пустышки
    test_funcs = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    if len(test_funcs) < len(suite.cases):
        return "AGENT_ERROR", f"Жульничество: сценариев было {len(suite.cases)}, а тестов в коде только {len(test_funcs)}. Не удаляй тесты!"

    for func in test_funcs:
        func_src = ast.get_source_segment(code, func) or ""
        if "requests." not in func_src:
            return "AGENT_ERROR", f"В тесте {func.name} нет реального HTTP-запроса через requests!"
        has_assert = any(isinstance(n, ast.Assert) for n in ast.walk(func))
        if not has_assert or "assert True" in func_src:
            return "AGENT_ERROR", f"В тесте {func.name} отсутствует осмысленный assert!"

    # Замок 4: Все ожидаемые статус-коды из сценариев обязаны остаться в коде
    expected_codes = {str(case.expected_status) for case in suite.cases}
    missing_codes = [c for c in expected_codes if c not in code]
    if missing_codes:
        return "AGENT_ERROR", f"Из кода пропали ожидаемые статус-коды из сценариев: {missing_codes}. Верни их в assert!"

    # Замок 5: Живой прогон против Testcontainers (Docker)
    result = subprocess.run(
        ["pytest", str(file_path), "-v", "--tb=short"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return "PASSED", "OK"

    # Код теста валиден, но упал против живого контейнера -> это расхождение сервиса со спекой!
    failed_lines = [line for line in result.stdout.splitlines() if line.startswith("FAILED ")]
    summary = "\n".join(failed_lines) if failed_lines else result.stdout[-1000:]
    return "SERVICE_MISMATCH", summary



def generate_pytest_with_healing(
    suite: TestSuite, 
    output_dir: str = "generated_tests", 
    target_filename: str = "test_pay.py",
    max_retries: int = 3
) -> Path:
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / target_filename
    messages = [
        {"role": "system", "content": load_skill("pytest_codegen")},
        {
            "role": "user",
            "content": f"Сгенерируй файл {target_filename} по этим сценариям:\n{suite.model_dump_json(indent=2)}",
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

        status, feedback = run_pytest_gate(file_path, suite)
        tracer.log(
            f"code_generation_attempt_{attempt}",
            "ollama_llm",
            {"status": status, "filename": file_path.name},
            t_start,
        )

        if status == "PASSED":
            print(f"✅ [Контур 2] Успех! Все 5 замков и Testcontainers пройдены с попытки #{attempt}!")
            return file_path

        if status == "SERVICE_MISMATCH":
            print(
                f"\n🚨 [РАСХОЖДЕНИЕ СЕРВИСА СО СПЕЦИФИКАЦИЕЙ] (Попытка #{attempt}):\n"
                f"Код сгенерированных тестов валиден (все AST-замки пройдены), но живой сервис ответил не по спеке:\n"
                f"{feedback}\n"
                f"Останавливаю цикл ретраев: требуется проверка бэкенда или спецификации человеком."
            )
            return file_path

        print(f"⚠️ [ОШИБКА АГЕНТА] Попытка #{attempt} не прошла AST-замки:\n{feedback}\nПередаю на самоисправление...")
        messages.append({"role": "assistant", "content": raw_code})
        messages.append(
            {
                "role": "user",
                "content": f"Код не прошёл проверку. Исправь ошибки по этому логу и верни полный исправленный файл:\n{feedback}",
            }
        )

    raise RuntimeError(f"Агент не смог добиться зелёных тестов за {max_retries} попытки.")

def update_test_registry(suite: TestSuite, test_file: Path, registry_path: str = "test_registry.json") -> None:
    """Регистрирует новые сгенерированные тесты в едином реестре трассируемости."""
    reg_file = Path(registry_path)
    registry = json.loads(reg_file.read_text(encoding="utf-8")) if reg_file.exists() else []
    existing_tcs = {item["tc_id"] for item in registry}

    for idx, case in enumerate(suite.cases, start=len(registry) + 1):
        tc_id = getattr(case, "id", None) or getattr(case, "tc_id", None) or f"TC-{idx:03d}"
        if case.action == "ADD" and tc_id not in existing_tcs:
            registry.append({
                "req_id": getattr(case, "req_id", "REQ-006"),
                "tc_id": tc_id,
                "test_file": str(test_file),
                "test_func": f"test_{tc_id.lower().replace('-', '_')}",
                "description": getattr(case, "title", None) or getattr(case, "description", str(case)),
                "status": "active",
            })

    reg_file.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"📒 Реестр {registry_path} обновлён (всего записей: {len(registry)}).")


if __name__ == "__main__":
    tracer.clear()
    delta_files = sorted(Path("generated_scenarios").glob("delta_req-*.json"))
    if delta_files:
        delta_path = delta_files[-1]
        req_slug = delta_path.stem.replace("delta_", "").replace("-", "_")  # например: req_006
        target_name = f"test_{req_slug}.py"
        print(f"📄 Читаю дельта-сценарии из {delta_path} -> генерирую {target_name}...")
        suite = TestSuite.model_validate_json(delta_path.read_text(encoding="utf-8"))
        out_file = generate_pytest_with_healing(suite, target_filename=target_name)
        update_test_registry(suite, out_file)
    else:
        scenarios_file = Path("generated_scenarios/payment_suite.json")
        suite = TestSuite.model_validate_json(scenarios_file.read_text(encoding="utf-8"))
        generate_pytest_with_healing(suite)


generate_pytest_from_suite = generate_pytest_with_healing
