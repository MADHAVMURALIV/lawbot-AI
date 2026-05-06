import os
import re
import json

INPUT_FOLDER = "data/cleaned"
OUTPUT_FOLDER = "data/structured"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def clean_text(text):

    # Fix missing spaces between words
    text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)

    # Add space after punctuation
    text = re.sub(r'([.,;:])([A-Za-z])', r'\1 \2', text)

    # Normalize spaces
    text = re.sub(r'\s+', ' ', text)

    return text


def extract_sections(text, act):

    sections = []

    # Detect section numbers like "1." "2." anywhere
    pattern = r'(\d+)\.'

    matches = list(re.finditer(pattern, text))

    for i in range(len(matches)):

        start = matches[i].start()
        sec_num = matches[i].group(1)

        if i + 1 < len(matches):
            end = matches[i+1].start()
        else:
            end = len(text)

        content = text[start:end].strip()

        sections.append({
            "act": act,
            "section": sec_num,
            "content": content
        })

    return sections


for file in os.listdir(INPUT_FOLDER):

    if not file.endswith(".txt"):
        continue

    path = os.path.join(INPUT_FOLDER, file)

    with open(path, "r", encoding="utf-8") as f:
        text = f.read()

    text = clean_text(text)

    act_name = file.replace(".txt","")

    sections = extract_sections(text, act_name)

    output_path = os.path.join(OUTPUT_FOLDER, act_name + ".json")

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, indent=2, ensure_ascii=False)

    print(file, "→", act_name + ".json", "sections:", len(sections))