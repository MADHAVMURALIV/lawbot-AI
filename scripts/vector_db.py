import json
import faiss
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "all-MiniLM-L6-v2"

CHUNKS_FILE = Path("data/rag/chunks.json")
DB_DIR = Path("data/rag/db")
DB_DIR.mkdir(parents=True, exist_ok=True)

with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
    chunks = json.load(f)

texts = [str(c.get("text", "")).strip() for c in chunks if str(c.get("text", "")).strip()]

filtered_chunks = [c for c in chunks if str(c.get("text", "")).strip()]

model = SentenceTransformer(EMBED_MODEL)

print("Creating RAG embeddings...")
embeddings = model.encode(
    texts,
    batch_size=64,
    show_progress_bar=True,
    convert_to_numpy=True
).astype("float32")

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

faiss.write_index(index, str(DB_DIR / "lawbot.index"))

with open(DB_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(filtered_chunks, f, ensure_ascii=False, indent=2)

print("RAG vector DB created successfully.")