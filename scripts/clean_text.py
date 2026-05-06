import re
from pathlib import Path

INPUT_DIR = Path("data/texts")
OUTPUT_DIR = Path("data/cleaned")
OUTPUT_DIR.mkdir(exist_ok=True)

def clean_text(text):

    idx = text.find("CHAPTER")
    if idx != -1:
        text = text[idx:]
    junk_patterns = [
        r"REGISTERED NO.*",
        r"MINISTRY OF LAW.*",
        r"THE GAZETTE OF INDIA.*",
        r"EXTRAORDINARY.*",
        r"PUBLISHED BY AUTHORITY.*"
    ]

    for pat in junk_patterns:
        text = re.sub(pat, "", text, flags=re.I)
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
    text = re.sub(r'([a-zA-Z])(\d)', r'\1 \2', text)
    text = re.sub(r'(\d)([a-zA-Z])', r'\1 \2', text)
    text = re.sub(r'\s+', ' ', text)

    return text.strip()


for file in INPUT_DIR.glob("*.txt"):

    print("Cleaning:", file.name)

    text = file.read_text(encoding="utf-8", errors="ignore")

    cleaned = clean_text(text)

    out_file = OUTPUT_DIR / file.name
    out_file.write_text(cleaned, encoding="utf-8")

print(" All files cleaned successfully.")