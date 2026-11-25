from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions

DB_PATH = "./chroma_db"
COLLECTION_NAME = "project_specs"

ru_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)


def get_client():
    return chromadb.PersistentClient(path=DB_PATH)


def get_collection():
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ru_ef,
    )


def ingest_specs(specs_dir: str = "specs") -> int:
    client = get_client()
    # Безопасно пересоздаем коллекцию средствами самой ChromaDB (без удаления папки на диске!)
    try:
        client.delete_collection(name=COLLECTION_NAME)
    except Exception:
        pass

    collection = get_collection()
    specs_path = Path(specs_dir)

    documents = []
    metadatas = []
    ids = []

    for file_path in specs_path.glob("*.md"):
        content = file_path.read_text(encoding="utf-8")
        documents.append(content)
        metadatas.append({"source": file_path.name})
        ids.append(file_path.stem)

    if documents:
        collection.upsert(
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

    return len(documents)


if __name__ == "__main__":
    count = ingest_specs()
    print(f"✅ Успешно загружено спецификаций в векторную базу: {count}")
