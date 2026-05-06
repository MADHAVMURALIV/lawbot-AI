import json
import faiss
from pathlib import Path
from sentence_transformers import SentenceTransformer

EMBED_MODEL = "all-MiniLM-L6-v2"

STRUCTURED_FILE = Path("data/structured/master_structured.json")
OUT_DIR = Path("data/structured_db")
OUT_DIR.mkdir(parents=True, exist_ok=True)

with open(STRUCTURED_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

print("Loaded structured data type:", type(data))
print("Number of records:", len(data))
if len(data) > 0:
    print("Sample keys:", list(data[0].keys()))
    print("Sample record:", data[0])

model = SentenceTransformer(EMBED_MODEL)

texts = []
metadata = []

for entry in data:
    if not isinstance(entry, dict):
        continue

    act = str(entry.get("act", "")).strip()
    section = str(entry.get("section", "")).strip()
    content = str(entry.get("content", "")).strip()

    if not act or not section or not content:
        continue

    combined = f"{act} section {section}. {content}"
    texts.append(combined)

    metadata.append({
        "act": act,
        "section": section,
        "content": content
    })

print("Valid structured records found:", len(texts))

if not texts:
    raise ValueError("No valid structured records found in master_structured.json")

print("Creating structured embeddings...")
embeddings = model.encode(
    texts,
    batch_size=64,
    show_progress_bar=True,
    convert_to_numpy=True
).astype("float32")

print("Embeddings shape:", embeddings.shape)

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

faiss.write_index(index, str(OUT_DIR / "structured.index"))

with open(OUT_DIR / "metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)

print("Structured FAISS index built successfully.")