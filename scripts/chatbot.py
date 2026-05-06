import json
import faiss
import re
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from scripts.llm_engine import generate_response
from scripts.translator import translate_to_english, translate_from_english


STRUCTURED_FILE = Path("data/structured/master_structured.json")

with open(STRUCTURED_FILE, "r", encoding="utf-8") as f:
    master_structured = json.load(f)

DB_DIR = Path("data/rag/db")
INDEX_FILE = DB_DIR / "lawbot.index"
META_FILE = DB_DIR / "metadata.json"

index = faiss.read_index(str(INDEX_FILE))

with open(META_FILE, "r", encoding="utf-8") as f:
    metadata = json.load(f)

STRUCT_INDEX = faiss.read_index("data/structured_db/structured.index")

with open("data/structured_db/metadata.json", "r", encoding="utf-8") as f:
    struct_metadata = json.load(f)


embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

CHAT_RESPONSES = {
    "hi": "Hello! I'm here to help with legal questions.",
    "hello": "Hello! I'm here to help with legal questions.",
    "hey": "Hello! I'm here to help with legal questions.",
    "how are you": "I'm here and ready to help with your legal queries.",
    "how are u": "I'm here and ready to help with your legal queries.",
    "thanks": "You're welcome. Ask me any legal question from the database.",
    "thank you": "You're welcome. Ask me any legal question from the database."
}

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "i", "me", "my", "mine", "he", "she", "it", "they", "them", "their",
    "we", "our", "ours", "you", "your", "yours",
    "and", "or", "but", "if", "then", "so", "because",
    "had", "has", "have", "do", "does", "did",
    "to", "of", "for", "in", "on", "at", "by", "with", "from", "as",
    "that", "this", "these", "those", "what", "which", "who", "whom",
    "when", "where", "why", "how", "can", "could", "would", "should",
    "may", "might", "shall", "will", "about", "under", "into", "over"
}


def normalize_text(text):
    text = str(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def clean_provision_text(text):
    text = normalize_text(text)

    replacements = [
        ("Whoevercommits", "Whoever commits"),
        ("shallbepunished", "shall be punished"),
        ("imprisonmentfor", "imprisonment for"),
        ("whichmayextendto", "which may extend to"),
        ("andshallalsobeliabletofine", "and shall also be liable to fine"),
        ("criminalintention", "criminal intention"),
        ("lawfulact", "lawful act"),
        ("propercareandcaution", "proper care and caution"),
        ("drivinglicence", "driving licence"),
        ("motorvehicle", "motor vehicle"),
        ("burdenofproof", "burden of proof"),
        ("electronicrecord", "electronic record")
    ]

    for old, new in replacements:
        text = text.replace(old, new)

    return text


def tokenize(text):
    text = normalize_text(text).lower()
    return re.findall(r"[a-zA-Z0-9]+", text)


def important_tokens(text):
    return [t for t in tokenize(text) if t not in STOPWORDS and len(t) > 2]

def detect_section_and_act(query):
    q = query.lower()

    sec_match = re.search(r"\bsection\s*(\d+[a-zA-Z]?)\b", q)
    section = sec_match.group(1) if sec_match else None

    act = None

    act_aliases = {
        "bns": "BNS",
        "bnss": "BNSS",
        "bsa": "BSA",
        "ipc": "IPC",
        "crpc": "CRPC",
        "constitution": "CONSTITUTION",
        "motor vehicles act": "MVD",
        "motor vehicle act": "MVD",
        "mvd": "MVD",
        "evidence act": "BSA"
    }

    for alias, canonical in act_aliases.items():
        if alias in q:
            act = canonical
            break

    return section, act


def is_chat_query(query):
    return query.lower().strip() in CHAT_RESPONSES


def is_section_lookup(query):
    return re.search(r"\bsection\s*\d+[a-zA-Z]?\b", query.lower()) is not None

def embed_query(query):
    embedding = embedding_model.encode([query], convert_to_numpy=True)
    return np.array(embedding).astype("float32")

def exact_section_lookup(section, act=None):
    results = []

    for item in master_structured:
        item_section = str(item.get("section", "")).strip().lower()
        item_act = str(item.get("act", "")).strip().upper()

        if item_section == str(section).strip().lower():
            if act is None or item_act == act.upper():
                results.append(item)

    return results

def search_structured(query, top_k=30, act_filter=None):
    qvec = embed_query(query)
    distances, indices = STRUCT_INDEX.search(qvec, top_k)

    results = []

    for idx, dist in zip(indices[0], distances[0]):
        if idx == -1:
            continue

        item = dict(struct_metadata[idx])

        if act_filter:
            if str(item.get("act", "")).upper() != act_filter.upper():
                continue

        similarity_score = 1.0 / (1.0 + float(dist))
        item["score"] = similarity_score

        results.append(item)

    return results

def search_rag(query, top_k=10):
    qvec = embed_query(query)
    distances, indices = index.search(qvec, top_k)

    results = []

    for idx, dist in zip(indices[0], distances[0]):
        if idx == -1:
            continue

        item = dict(metadata[idx])
        similarity_score = 1.0 / (1.0 + float(dist))
        item["score"] = similarity_score

        results.append(item)

    return results

def item_full_text(item):
    return " ".join([
        str(item.get("act", "")),
        str(item.get("section", "")),
        str(item.get("title", "")),
        str(item.get("heading", "")),
        str(item.get("chapter", "")),
        str(item.get("content", "")),
        str(item.get("text", "")),
    ])


def score_candidate(query, item):
    q_tokens = set(important_tokens(query))
    item_text = item_full_text(item).lower()
    item_tokens = set(important_tokens(item_text))

    overlap_tokens = q_tokens & item_tokens
    overlap_score = len(overlap_tokens)

    vector_score = float(item.get("score", 0.0))

    coverage_score = overlap_score / max(len(q_tokens), 1)

    heading_bonus = 0

    heading_text = " ".join([
        str(item.get("title", "")),
        str(item.get("heading", "")),
        str(item.get("chapter", ""))
    ]).lower()

    first_line = item_text.split("\n")[0] if "\n" in item_text else item_text[:150]

    for token in q_tokens:
        if token in heading_text:
            heading_bonus += 3
        elif token in first_line:
            heading_bonus += 2

    phrase_bonus = 0
    query_lower = query.lower().strip()

    query_words = [w for w in important_tokens(query_lower) if len(w) > 3]

    dynamic_phrases = []

    dynamic_phrases.append(query_lower)

    for i in range(len(query_words) - 1):
        dynamic_phrases.append(
            query_words[i] + " " + query_words[i + 1]
        )

    for i in range(len(query_words) - 2):
        dynamic_phrases.append(
            query_words[i] + " " + query_words[i + 1] + " " + query_words[i + 2]
        )

    dynamic_phrases = list(set(dynamic_phrases))

    for phrase in dynamic_phrases:
        if phrase and phrase in item_text:
            phrase_bonus += 2

    generic_words = {
        "punishment", "offence", "offences", "law", "illegal",
        "act", "section", "person", "whoever", "shall",
        "under", "within", "such", "provided"
    }

    matched_specific_tokens = [
        token for token in overlap_tokens
        if token not in generic_words
    ]

    mismatch_penalty = 0

    if overlap_score <= 1:
        mismatch_penalty -= 5

    if len(matched_specific_tokens) == 0:
        mismatch_penalty -= 6

    specificity_bonus = len(matched_specific_tokens) * 1.5

    section_bonus = 0
    section, act = detect_section_and_act(query)

    if section and str(item.get("section", "")).lower() == section.lower():
        section_bonus += 10

    if act and str(item.get("act", "")).upper() == act.upper():
        section_bonus += 5

    important_legal_words = {
        "murder": 8,
        "rape": 8,
        "theft": 10,
        "cheating": 10,
        "cheat": 8,
        "dishonest": 8,
        "fraud": 9,
        "robbery": 10,
        "assault": 8,
        "hurt": 7,
        "grievous": 7,
        "kidnapping": 8,
        "dowry": 8,
        "negligence": 7,
        "drunk": 7,
        "driving": 7,
        "vehicle": 6,
        "accident": 7,
        "injury": 6,
        "death": 7,
        "weapon": 6,
        "knife": 6,
        "gun": 6,
        "stolen": 8,
        "steal": 9,
        "property": 7,
        "extortion": 8,
        "misappropriation": 8,
        "breach": 7,
        "trust": 7
    }

    keyword_bonus = 0

    for token in q_tokens:
        if token in important_legal_words and token in item_text:
            keyword_bonus += important_legal_words[token]

    bnss_penalty = 0

    criminal_keywords = {
        "murder", "rape", "theft", "cheating", "fraud",
        "assault", "robbery", "hurt", "kidnapping",
        "dowry", "extortion", "criminal", "death"
    }

    if any(word in query_lower for word in criminal_keywords):
        if str(item.get("act", "")).upper() == "BNSS":
            bnss_penalty -= 12

    offence_section_bonus = 0

    offence_queries = {
        "theft": ["303"],
        "cheating": ["318"],
        "fraud": ["318"],
        "rape": ["65"],
        "murder": ["109"],
        "robbery": ["309"],
        "kidnapping": ["137"],
        "grievous": ["117"],
        "assault": ["131"]
    }

    for offence, preferred_sections in offence_queries.items():
        if offence in query_lower:
            if str(item.get("section", "")).strip() in preferred_sections:
                offence_section_bonus += 15

    wrong_act_penalty = 0

    criminal_queries = {
        "murder", "rape", "theft", "cheating", "fraud",
        "assault", "robbery", "hurt", "grievous",
        "kidnapping", "dowry", "extortion"
    }

    if any(word in query_lower for word in criminal_queries):
        item_act = str(item.get("act", "")).upper()

        allowed_acts = {
            "BNS",
            "IPC",
            "BNSS",
            "CRPC",
            "BSA",
            "EVIDENCE",
            "MVD",
            "POCSO",
            "NDPS",
            "IT",
            "CONSTITUTION",
            "COMPANY",
            "CONSUMER"
        }

        weak_match_acts = {
            "COMPANY",
            "CONSUMER",
            "CONSTITUTION"
        }

        if item_act in weak_match_acts:
            wrong_act_penalty -= 10

    total_score = (
        (vector_score * 10)
        + (overlap_score * 2)
        + (coverage_score * 8)
        + heading_bonus
        + phrase_bonus
        + specificity_bonus
        + section_bonus
        + mismatch_penalty
        + keyword_bonus
        + bnss_penalty
        + offence_section_bonus
        + wrong_act_penalty
    )

    return total_score
def rerank_results(query, results):
    ranked = []

    for item in results:
        item_copy = dict(item)
        item_copy["rank_score"] = score_candidate(query, item_copy)
        ranked.append(item_copy)

    ranked.sort(key=lambda x: x["rank_score"], reverse=True)
    return ranked


def deduplicate_results(results):
    seen = set()
    final_results = []

    for item in results:
        key = (
            str(item.get("act", "")).upper(),
            str(item.get("section", "")).strip()
        )

        if key not in seen:
            seen.add(key)
            final_results.append(item)

    return final_results

def format_primary_law(item):
    act = item.get("act", "Unknown")
    section = item.get("section", "Unknown")

    provision = item.get("content") or item.get("text") or ""
    provision = clean_provision_text(provision)

    return f"""Primary Law:
Act: {act}
Section: {section}
Provision: {provision}"""


def format_multiple_laws(items):
    lines = ["Most Relevant Legal Provisions:"]

    for item in items:
        act = item.get("act", "Unknown")
        section = item.get("section", "Unknown")
        provision = item.get("content") or item.get("text") or ""
        provision = clean_provision_text(provision)

        if len(provision) > 500:
            provision = provision[:500] + "..."

        lines.append(
            f"""
- Act: {act}
  Section: {section}
  Provision: {provision}
"""
        )

    return "\n".join(lines)

def answer_chat(query):
    return CHAT_RESPONSES.get(
        query.lower().strip(),
        "Hello! I'm here to help with legal questions."
    )


def answer_section_lookup(query):
    section, act = detect_section_and_act(query)

    if not section:
        return "Relevant legal section not found in database."

    exact_matches = exact_section_lookup(section, act)

    if exact_matches:
        return format_primary_law(exact_matches[0])

    semantic_results = search_structured(query, top_k=10, act_filter=act)

    if semantic_results:
        ranked = rerank_results(query, semantic_results)
        return format_primary_law(ranked[0])

    return "Relevant legal section not found in database."


def answer_general_query(query):
    structured_results = search_structured(query, top_k=150)

    ranked_results = rerank_results(query, structured_results)
    ranked_results = deduplicate_results(ranked_results)

    ranked_results = [
        r for r in ranked_results
        if r.get("rank_score", 0) > 8
    ]

    if not ranked_results:
        return "Relevant legal provision not found in database."

    top_results = ranked_results[:5]

    context_parts = []

    for result in top_results:
        act = str(result.get("act", "Unknown"))
        section = str(result.get("section", "Unknown"))
        provision = clean_provision_text(
            result.get("content")
            or result.get("text")
            or ""
        )

        if provision:
            context_parts.append(
                f"Act: {act}\n"
                f"Section: {section}\n"
                f"Provision: {provision}"
            )

    context = "\n\n".join(context_parts)

    prompt = f"""
You are a legal assistant.

The user asked:
{query}

Below are the most relevant legal provisions:

{context}

Instructions:
1. Answer in simple language.
2. Start with the single most relevant law first.
3. Mention section number, punishment, imprisonment, fine, or penalty.
4. Only mention additional sections if they are directly relevant.
5. Do not mention unrelated procedural sections like medical examination unless the user asks.
6. Keep the response under 150 words.
7. Use short paragraphs.
8. Do not repeat the same punishment multiple times.
9. Do not invent legal details.


"""

    try:
        answer = generate_response(prompt)

        if answer and len(answer.strip()) > 0:
            return answer.strip()

    except Exception as e:
        print("LLM summarization error:", e)

    # Fallback if LLM fails
    fallback = []

    for result in top_results:
        fallback.append(
            f"- Act: {result.get('act', 'Unknown')}\n"
            f"  Section: {result.get('section', 'Unknown')}\n"
            f"  Provision: {clean_provision_text(result.get('content') or result.get('text') or '')[:300]}..."
        )

    return "Most Relevant Legal Provisions:\n\n" + "\n\n".join(fallback)

def chatbot_response(user_query):
    user_query = normalize_text(user_query)

    if not user_query:
        return "Please enter a legal question."

    original_query = user_query

    try:
        translated_query = translate_to_english(user_query)
    except Exception:
        translated_query = user_query

    query = translated_query.strip()

    if is_chat_query(query):
        answer = answer_chat(query)
    elif is_section_lookup(query):
        answer = answer_section_lookup(query)
    else:
        answer = answer_general_query(query)

    try:
        final_answer = translate_from_english(answer, original_query)
        return final_answer
    except Exception:
        return answer

if __name__ == "__main__":
    print("LAW BOT:\n")
    print("Hello! I'm here to help with legal questions.")
    print("\n" + "=" * 80)

    while True:
        user_query = input("\nUSER:\n").strip()

        if user_query.lower() in {"exit", "quit"}:
            print("\nLAW BOT:\n")
            print("Goodbye.")
            break

        try:
            response = chatbot_response(user_query)

            print("\nLAW BOT:\n")
            print(response)

        except Exception as e:
            print("\nLAW BOT:\n")
            print(f"Error generating response: {e}")

        print("\n" + "=" * 80)