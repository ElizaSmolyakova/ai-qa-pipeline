import re
from pathlib import Path
import chromadb

COLLECTION_NAME = "project_specs"
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def get_next_req_id(collection) -> str:
    """Автоматически генерирует следующий свободный REQ-XXX на основе записей в базе."""
    existing = collection.get(include=["metadatas"])
    max_num = 0
    for meta in existing["metadatas"]:
        match = re.match(r"REQ-(\d+)", meta.get("req_id", ""))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"REQ-{max_num + 1:03d}"


def ingest_requirements(specs_dir: str = "specs") -> int:
    try:
        chroma_client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    pattern = re.compile(r"-\s*\[REQ\]\s*\[([a-zA-Z0-9_-]+)\]\s*(.+)")

    created_ids = []
    for md_file in sorted(Path(specs_dir).glob("*.md")):
        for line in md_file.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line.strip())
            if match:
                domain, text = match.groups()
                req_id = get_next_req_id(collection)
                doc_id = f"{req_id}_v1"
                collection.add(
                    ids=[doc_id],
                    documents=[f"[{req_id}] [{domain}] {text}"],
                    metadatas=[{
                        "req_id": req_id,
                        "domain": domain,
                        "version": 1,
                        "status": "active",
                        "overrides": "",
                        "overridden_by": "",
                    }],
                )
                created_ids.append(doc_id)

    print(f"✅ Загружено активных требований с авто-ID: {len(created_ids)} шт. ({created_ids})")
    return len(created_ids)


if __name__ == "__main__":
    ingest_requirements()
