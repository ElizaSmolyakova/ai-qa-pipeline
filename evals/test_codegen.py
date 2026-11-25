import ast
from src.code_generator import generate_pytest_from_suite
from src.generator import generate_test_suite


def test_generated_code_matches_scenarios_and_has_asserts(tmp_path):
    # 1. Получаем проверенный набор сценариев
    suite = generate_test_suite("Составь позитивные и негативные тесты для сервиса оплаты")

    # 2. Генерируем .py файл ВО ВРЕМЕННУЮ ПАПКУ (tmp_path), не трогая рабочую generated_tests/!
    file_path = generate_pytest_from_suite(suite, output_dir=str(tmp_path))
    code = file_path.read_text(encoding="utf-8")

    # 3. Разбираем код в синтаксическое дерево Python (AST)
    tree = ast.parse(code)

    test_functions = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]

    assert len(test_functions) == len(suite.cases), (
        f"Ожидалось {len(suite.cases)} автотестов, а сгенерировано {len(test_functions)}"
    )

    for func in test_functions:
        has_assert = any(isinstance(node, ast.Assert) for node in ast.walk(func))
        assert has_assert, f"В сгенерированном тесте '{func.name}' нет ни одного assert!"

    for case in suite.cases:
        assert str(case.expected_status) in code, (
            f"Статус-код {case.expected_status} из сценария '{case.title}' потерялся при генерации кода!"
        )

    assert "example.com" not in code, "Галлюцинация домена! Модель попыталась отправить тесты на example.com"
    assert "base_url" in code, "Модель забыла использовать фикстуру base_url для URL!"
