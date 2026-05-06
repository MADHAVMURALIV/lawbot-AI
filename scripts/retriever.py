import faiss
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path

DB_DIR = Path("data/rag/db")

index = faiss.read_index(str(DB_DIR / "lawbot.index"))

with open(DB_DIR / "metadata.json", "r", encoding="utf-8") as f:
    metadata = json.load(f)

model = SentenceTransformer("all-MiniLM-L6-v2")

def retrieve(query, k=5):

    query_embedding = model.encode([query]).astype("float32")

    D, I = index.search(query_embedding, k)

    results = []

    for idx in I[0]:
        results.append(metadata[idx])

    return results