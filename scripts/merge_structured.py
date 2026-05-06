import json
from pathlib import Path

STRUCTURED_DIR = Path("data/structured")
OUTPUT_FILE = STRUCTURED_DIR / "master_structured.json"

all_data = []
seen = set()

for file in STRUCTURED_DIR.glob("*.json"):

    if file.name in ["master_structured.json", "laws.json"]:
        continue

    print("Merging:", file.name)

    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

        for entry in data:

            key = (entry.get("act"), entry.get("section"), entry.get("content"))

            if key not in seen:
                seen.add(key)
                all_data.append(entry)

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(all_data, f, indent=2)

print(" Master structured DB created.")
print("Total sections:", len(all_data))