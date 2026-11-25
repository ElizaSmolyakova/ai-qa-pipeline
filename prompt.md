Контекст проекта `ai-qa-pipeline` (SDD + RAG + LLM Evals на Python):
- Стек: Python 3.11, ChromaDB (`paraphrase-multilingual-MiniLM-L12-v2`), локальная Ollama (`qwen2.5-coder:1.5b`), Pydantic, Pytest, FastAPI (`uvicorn`).
- Что уже сделано и работает (все тесты зелёные):
  1. `specs/` (`payment.md`, `auth.md`) -> `src/ingest.py` загружает требования в локальную ChromaDB.
  2. `src/generator.py` + `src/schemas.py` генерируют типизированный `TestSuite` (с разделением `http_method` и `endpoint`).
  3. `src/code_generator.py` превращает `TestSuite` в готовый `.py` файл в `generated_tests/` с использованием фикстуры `base_url` (из `generated_tests/conftest.py`).
  4. `evals/` (`test_retrieval.py`, `test_quality.py`, `test_codegen.py`) валидируют поиск, покрытие, AST-синтаксис и проводят ревью через LLM-as-a-Judge.
  5. `app/main.py` — мок-сервис на FastAPI (`POST /api/v1/pay`), против которого сгенерированные тесты успешно проходят.
  6. `FINDINGS.md` — зафиксированы найденные баги LLM и закрывающие их Quality Gates.

Что хотим делать дальше (на выбор):
1. Упаковать FastAPI-сервис в Docker и запускать прогон `generated_tests/` автоматически через `Testcontainers` (плюс попробовать mutation testing).
2. Добавить версионность спецификаций (`specs/v1` vs `specs/v2`) и Diff-генерацию тестов при изменении требований.
3. Ускорить `evals/` через маркеры `@pytest.mark.slow` (разделить быстрые проверки от вызовов Ollama).
