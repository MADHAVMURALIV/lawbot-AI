from langdetect import detect
from deep_translator import GoogleTranslator


LANG_MAP = {
    "en": "English",
    "hi": "Hindi",
    "ml": "Malayalam",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "bn": "Bengali",
    "gu": "Gujarati",
    "mr": "Marathi",
    "pa": "Punjabi",
    "ur": "Urdu"
}

def detect_language(text):
    try:
        lang_code = detect(text)
        return LANG_MAP.get(lang_code, "English")
    except:
        return "English"

def translate_to_english(text, source_lang):
    if source_lang == "English":
        return text

    try:
        translated = GoogleTranslator(
            source="auto",
            target="en"
        ).translate(text)
        return translated
    except:
        return text


def translate_from_english(text, target_lang):
    if target_lang == "English":
        return text

    try:
        translated = GoogleTranslator(
            source="en",
            target=target_lang.lower()
        ).translate(text)
        return translated
    except:
        return text