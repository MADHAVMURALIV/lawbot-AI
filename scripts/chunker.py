from pathlib import Path
import json
import re

TEXT_DIR = Path("data/texts")
OUT_DIR = Path("data/rag")

OUT_DIR.mkdir(exist_ok=True)

all_chunks = []


def clean(text):

    # remove Gazette headers
    text = re.sub(r'THEGAZETTEOFINDIAEXTRAORDINARY.*?\n', '\n', text)

    # remove chapter headings
    text = re.sub(r'CHAPTER\s+[IVXLC]+\s*\n.*?\n', '\n', text)

    # remove section index pages
    text = re.sub(r'SECTIONS\s+.*?\n', '\n', text)

    # fix broken section numbers like:
    # 1\n0. → 10.
    text = re.sub(r'\n(\d)\n(\d)\.', r'\n\1\2.', text)

    # remove isolated page numbers
    text = re.sub(r'\n\d+\n', '\n', text)

    # normalize spaces
    text = re.sub(r'[ \t]+', ' ', text)

    # fix merged lowercase-uppercase words
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    # fix common merged legal words
    text = re.sub(r'([a-z])\bshall\b', r'\1 shall', text)
    text = re.sub(r'([a-z])\bperson\b', r'\1 person', text)
    text = re.sub(r'([a-z])\bpunished\b', r'\1 punished', text)
    text = re.sub(r'([a-z])\bimprisonment\b', r'\1 imprisonment', text)
    text = re.sub(r'\n0+\.', '\n', text)
    # ensure section numbers start on new lines
    text = re.sub(r'(?<!\n)(\d{1,3})\.\s+', r'\n\1. ', text)

    # remove duplicate newlines
    text = re.sub(r'\n+', '\n', text)

    return text.strip()

def split_sections(text):

    # match section numbers with or without spaces
    pattern = r'\n?(\d{1,3})\.(.*?)(?=\n?\d{1,3}\.|$)'

    matches = re.findall(pattern, text, re.S)

    sections = []

    for num, content in matches:

        num = num.strip()

        # remove fake sections like 000 or 00
        if num.startswith("0"):
            continue

        if int(num) > 600:
            continue

        sections.append({
            "section": num,
            "text": f"{num}. {content.strip()}"
        })

    return sections

def word_chunks(text, size=400):

    words = text.split()

    return [
        " ".join(words[i:i+size])
        for i in range(0, len(words), size)
    ]


for file in TEXT_DIR.glob("*.txt"):

    print("Processing:", file.name)

    text = file.read_text(encoding="utf-8")

    text = clean(text)

    sections = split_sections(text)

    if len(sections) == 0:

        print("No sections detected → fallback chunking")

        sections = word_chunks(text)

    for sec in sections:

        if isinstance(sec, dict):

            all_chunks.append({
                "id": f"{file.stem}_{sec['section']}",
                "act": file.stem,
                "section": sec["section"],
                "text": sec["text"]
            })

        else:

        # fallback chunks have no section numbers
            all_chunks.append({
                "id": f"{file.stem}_chunk_{len(all_chunks)}",
                "act": file.stem,
                "section": "Unknown",
                "text": sec
            })

merged = {}

for chunk in all_chunks:

    key = chunk["id"]

    if key not in merged:
        merged[key] = chunk
    else:
        merged[key]["text"] += " " + chunk["text"]

all_chunks = list(merged.values())
all_chunks = sorted(
    all_chunks,
    key=lambda x: (x["act"], int(x["section"]) if str(x["section"]).isdigit() else 9999)
)
with open(OUT_DIR / "chunks.json", "w", encoding="utf-8") as f:

    json.dump(all_chunks, f, indent=2)


print("Chunks saved.")
print("Total chunks:", len(all_chunks))