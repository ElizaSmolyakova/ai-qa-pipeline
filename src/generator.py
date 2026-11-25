import time
from pathlib import Path
import chromadb
from openai import OpenAI
from src.schemas import JudgeVerdict, TestSuite
from src.skills_loader import load_skill
from src.telemetry.tracer import tracer
from src.ingest import COLLECTION_NAME

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def evaluate_design_gate(spec_context: str, suite: TestSuite) -> tuple[bool, str]:
    """Quality Gate 1: минимум 4 сценария + проверка LLM-судьёй."""
    if len(suite.cases) < 4:
        return False, f"Слишком мало сценариев ({len(suite.cases)}). Покрой позитивные, граничные и негативные ветки (минимум 4)."

    judge_resp = client.beta.chat.completions.parse(
        model="qwen2.5-coder:3b",
        temperature=0.0,
        messages=[
            {"role": "system", "content": load_skill("llm_judge")},
            {
                "role": "user",
                "content": f"Спецификация:\n{spec_context}\n\nСгенерированные сценарии:\n{suite.model_dump_json(indent=2)}",
            },
        ],
        response_format=JudgeVerdict,
    )
    verdict = judge_resp.choices[0].message.parsed
    if verdict.score >= 4 and verdict.passed:
        return True, "OK"
    return False, f"Оценка судьи: {verdict.score}/5. Замечания: {verdict.critique}"


def generate_test_suite(query: str, max_retries: int = 3) -> TestSuite:
    t0 = time.time()
    collection = chroma_client.get_collection(COLLECTION_NAME)
    results = collection.query(query_texts=[query], n_results=2)
    docs = results["documents"][0]
    context = "\n---\n".join(docs)
    tracer.log("retrieval", "chromadb", {"query": query, "chunks": len(docs)}, t0)

    messages = [
        {"role": "system", "content": load_skill("test_designer")},
        {"role": "user", "content": f"Спецификация:\n{context}\n\nЗадача: {query}"},
    ]

    for attempt in range(1, max_retries + 1):
        print(f"\n🧠 [Контур 1] Попытка тест-дизайна #{attempt} из {max_retries}...")
        t_attempt = time.time()

        response = client.beta.chat.completions.parse(
            model="qwen2.5-coder:3b",
            temperature=0.0 if attempt == 1 else 0.2,
            messages=messages,
            response_format=TestSuite,
        )
        suite = response.choices[0].message.parsed

        passed, feedback = evaluate_design_gate(context, suite)
        tracer.log(
            f"test_design_attempt_{attempt}",
            "ollama_llm",
            {"passed": passed, "cases_count": len(suite.cases)},
            t_attempt,
        )

        if passed:
            out_dir = Path("generated_scenarios")
            out_dir.mkdir(exist_ok=True)
            out_file = out_dir / "payment_suite.json"
            out_file.write_text(suite.model_dump_json(indent=2), encoding="utf-8")
            print(f"✅ [Контур 1] Сценарии ({len(suite.cases)} шт.) сохранены в {out_file} (попытка #{attempt})!")
            return suite

        print(f"❌ [Контур 1] Попытка #{attempt} отклонена судьёй:\n{feedback}\nДорабатываю сценарии...")
        messages.append({"role": "assistant", "content": suite.model_dump_json()})
        messages.append(
            {
                "role": "user",
                "content": f"Сценарии не прошли проверку качества. Исправь их по замечаниям и верни полный обновлённый набор:\n{feedback}",
            }
        )

    raise RuntimeError(f"Контур 1 не смог спроектировать качественные сценарии за {max_retries} попытки.")


if __name__ == "__main__":
    tracer.clear()
    generate_test_suite("Составь позитивные и негативные тесты для сервиса оплаты")
