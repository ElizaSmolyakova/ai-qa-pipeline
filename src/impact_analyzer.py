import json
import re
import sys
from pathlib import Path
import chromadb
from openai import OpenAI
from src.ingest import COLLECTION_NAME, get_next_req_id
from src.schemas import ImpactReport
from src.skills_loader import load_skill

client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def analyze_incoming_requirement(req_file_path: str) -> ImpactReport:
    raw_text = Path(req_file_path).read_text(encoding="utf-8").strip()
    match = re.search(r"\[REQ\]\s*\[([a-zA-Z0-9_-]+)\]\s*(.+)", raw_text)
    if not match:
        raise ValueError("Файл требования должен содержать формат: - [REQ] [domain] Текст")

    domain, req_body = match.groups()
    collection = chroma_client.get_collection(COLLECTION_NAME)
    new_req_id = get_next_req_id(collection)

    # 1. Ищем похожие по смыслу АКТИВНЫЕ требования с фильтром близости
    results = collection.query(
        query_texts=[req_body],
        n_results=3,
        where={"status": "active"},
        include=["documents", "distances"],
    )
    docs = results["documents"][0] if results["documents"] else []
    dists = results["distances"][0] if results["distances"] else []
    existing_docs = [doc for doc, dist in zip(docs, dists) if dist < 1.1]
    context = "\n".join(existing_docs) if existing_docs else "Активных требований не найдено."

    print(f"\n🔍 [Impact Analyzer] Присвоен ID: {new_req_id} [{domain}]")
    print(f"📚 Найдены похожие активные требования в базе:\n{context}\n")

    # 2. LLM определяет тип влияния и затронутые требования
    response = client.beta.chat.completions.parse(
        model="qwen2.5-coder:3b",
        temperature=0.0,
        messages=[
            {"role": "system", "content": load_skill("impact_analyzer")},
            {
                "role": "user",
                "content": (
                    f"Новое требование: [{new_req_id}] [{domain}] {req_body}\n\n"
                    f"Существующие активные требования:\n{context}"
                ),
            },
        ],
        response_format=ImpactReport,
    )
    report = response.choices[0].message.parsed
    report.new_req_id = new_req_id

    # 3. Обновляем связки и статусы в метаданных ChromaDB
    if report.affected_req_ids:
        for old_id in report.affected_req_ids:
            old_records = collection.get(where={"$and": [{"req_id": old_id}, {"status": "active"}]})
            for doc_id, meta in zip(old_records["ids"], old_records["metadatas"]):
                if report.impact_type == "FULL_OVERRIDE":
                    meta["status"] = "deprecated"
                    meta["overridden_by"] = new_req_id
                    print(f"🗄️ {doc_id} -> status: deprecated (полностью заменено на {new_req_id})")
                elif report.impact_type == "PARTIAL_OVERRIDE":
                    prev = meta.get("overridden_by", "")
                    meta["overridden_by"] = f"{prev},{new_req_id}".strip(",")
                    print(f"🔗 Связка: {doc_id} остаётся active, добавлено исключение overridden_by={new_req_id}")
                collection.update(ids=[doc_id], metadatas=[meta])

    # 4. Сохраняем новое требование в базу со связкой overrides
    collection.upsert(
        ids=[f"{new_req_id}_v1"],
        documents=[f"[{new_req_id}] [{domain}] {report.merged_rule}"],
        metadatas=[{
            "req_id": new_req_id,
            "domain": domain,
            "version": 1,
            "status": "active",
            "impact_type": report.impact_type,
            "overrides": ",".join(report.affected_req_ids),
            "overridden_by": "",
        }],
    )

    # 5. Сохраняем задание на дельта-автоматизацию для Контура 1
    out_dir = Path("generated_scenarios")
    out_dir.mkdir(exist_ok=True)
    delta_file = out_dir / "delta_task.json"
    delta_file.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    print(f"\n📊 Вердикт анализатора ({new_req_id}):")
    print(f"   • Тип влияния: {report.impact_type}")
    print(f"   • Связанные требования (overrides): {report.affected_req_ids}")
    print(f"   • Задание на дельта-тесты сохранено в: {delta_file}\n")
    return report


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "incoming_reqs/REQ-145.md"
    analyze_incoming_requirement(path)
