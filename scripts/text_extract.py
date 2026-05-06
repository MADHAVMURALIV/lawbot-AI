import pdfplumber
from pathlib import Path

PDF_DIR = Path("data/pdfs")
OUTPUT_DIR = Path("data/texts")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text += t + "\n"
    return text
pdf_files = list(PDF_DIR.glob("*.pdf"))
for pdf in pdf_files:
    print("Processing:", pdf.name)
    text = extract_text(pdf)
    out_file = OUTPUT_DIR / f"{pdf.stem}.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved:", out_file)