import hashlib
import re
from pathlib import Path
import chromadb

COLLECTION_NAME = "project_specs"
chroma_client = chromadb.PersistentClient(path="./chroma_db")


def get_next_req_id(collection) -> str:
    """Автоматически генерирует следующий свободный REQ-XXX на основе всех записей в базе."""
    existing = collection.get(include=["metadatas"])
    max_num = 0
    for meta in existing["metadatas"]:
        match = re.match(r"REQ-(\d+)", meta.get("req_id", ""))
        if match:
            max_num = max(max_num, int(match.group(1)))
    return f"REQ-{max_num + 1:03d}"


def ingest_requirements(dirs: tuple[str, ...] = ("specs", "incoming_reqs")) -> int:
    """Дозагружает новые требования из папок без удаления истории и без дубликатов."""
    collection = chroma_client.get_or_create_collection(name=COLLECTION_NAME)
    existing = collection.get(include=["metadatas"])
    existing_hashes = {meta.get("text_hash") for meta in existing["metadatas"] if meta.get("text_hash")}

    pattern = re.compile(r"-\s*\[REQ\]\s*\[([a-zA-Z0-9_-]+)\]\s*(.+)")
    added_ids = []

    for folder in dirs:
        folder_path = Path(folder)
        if not folder_path.exists():
            continue
        for md_file in sorted(folder_path.glob("*.md")):
            for line in md_file.read_text(encoding="utf-8").splitlines():
                match = pattern.match(line.strip())
                if not match:
                    continue
                domain, text = match.groups()
                text_hash = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:16]
                if text_hash in existing_hashes:
                    continue  # Уже есть в базе — не плодим дубли и не сдвигаем ID!

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
                        "text_hash": text_hash,
                        "overrides": "",
                        "overridden_by": "",
                    }],
                )
                existing_hashes.add(text_hash)
                added_ids.append(doc_id)

    total = collection.count()
    print(f"✅ Новых требований добавлено: {len(added_ids)} ({added_ids}). Всего в базе: {total} шт.")
    return len(added_ids)


if __name__ == "__main__":
    ingest_requirements()


def get_collection():
    """Совместимость для evals/test_retrieval.py"""
    return chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def ingest_specs(specs_dir: str = "specs") -> int:
    """Совместимость для evals/test_retrieval.py"""
    return ingest_requirements(dirs=(specs_dir,))


def get_collection():
    """Совместимость для evals/test_retrieval.py"""
    return chroma_client.get_or_create_collection(name=COLLECTION_NAME)


def ingest_specs(specs_dir: str = "specs") -> int:
    """Совместимость для evals/test_retrieval.py"""
    return ingest_requirements(dirs=(specs_dir,))
