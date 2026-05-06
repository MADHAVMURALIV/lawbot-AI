import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "phi3"

def generate_response(prompt: str) -> str:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "").strip()
    except Exception as e:
        return f"Error generating response: {e}"