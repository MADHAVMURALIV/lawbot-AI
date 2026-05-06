from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from flask_bcrypt import Bcrypt
import datetime
import re
import os
import sys
from flask_mail import Mail, Message
import random
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from scripts.chatbot import chatbot_response
from scripts.translator import (
    detect_language,
    translate_to_english,
    translate_from_english
)

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'tracksiumtechnologies@gmail.com'
app.config['MAIL_PASSWORD'] = 'dlhq nccl iitj oocv'

mail = Mail(app)

def init_auth_db():
    conn = sqlite3.connect("auth.db", timeout=10)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS users_auth (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME
    )
    """)
    conn.commit()
    conn.close()

init_auth_db()

otp_store = {}
otp_verified_users = set()

chat_history = []

LAST_QUERY_CONTEXT = {
    "query": "",
    "topic": ""
}

FOLLOW_UP_WORDS = {
    "minor", "child", "victim", "women", "woman",
    "punishment", "fine", "sentence", "what if",
    "if", "juvenile", "attempt", "abetment",
    "under", "below", "age", "death", "injury",
    "weapon", "knife", "gun", "rape", "murder",
    "robbery", "theft", "assault", "vehicle",
    "registration", "licence", "license", "permit"
}

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "being", "to", "of", "for", "in", "on", "at", "by", "with",
    "from", "as", "that", "this", "these", "those", "what", "which",
    "who", "whom", "when", "where", "why", "how", "can", "could",
    "would", "should", "may", "might", "shall", "will", "and", "or",
    "but", "if", "then", "so", "because", "about", "under", "into",
    "over", "law", "legal", "section", "provision", "please", "tell",
    "me", "about"
}

def tokenize_simple(text):
    return re.findall(r"[a-zA-Z0-9]+", str(text).lower())

def important_tokens_simple(text):
    return [
        token for token in tokenize_simple(text)
        if token not in STOPWORDS and len(token) > 2
    ]

def extract_topic(query):
    tokens = important_tokens_simple(query)
    important_words = [
        token for token in tokens
        if token not in {
            "punishment", "fine", "imprisonment",
            "sentence", "penalty", "liable"
        }
    ]
    return " ".join(important_words[:5])

def enrich_followup_query(query):
    q = str(query).lower().strip()
    token_count = len(important_tokens_simple(q))
    short_query = token_count <= 4

    followup_starters = (
        q.startswith("if ")
        or q.startswith("what if")
        or q.startswith("and ")
        or q.startswith("for minor")
        or q.startswith("for child")
        or q.startswith("if victim")
    )

    is_followup = (
        short_query
        or followup_starters
        or any(word in q for word in FOLLOW_UP_WORDS)
    )

    previous_topic = LAST_QUERY_CONTEXT.get("topic", "")

    if is_followup and previous_topic:
        return f"{previous_topic} {query}"

    return query

@app.route("/")
def landing():
    return render_template("landing.html")

@app.route("/bruh")
def bruh_page():
    return render_template("bruh.html")

@app.route("/chatbot")
def chatbot_page():
    return render_template("chatbot.html")

@app.route("/signin")
def signin_page():
    return render_template("signin.html")

@app.route("/signup_page")
def signup_page():
    return render_template("signup.html")

@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Backend is running"})

@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email required"}), 400

    otp = str(random.randint(100000, 999999))

    otp_store[email] = {
        "otp": otp,
        "expiry": time.time() + 300
    }

    try:
        msg = Message(
            subject="LawBot OTP Verification",
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Your OTP is: {otp}\nValid for 5 minutes."
        mail.send(msg)
        return jsonify({"message": "OTP sent successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.get_json()
    email = data.get("email")
    user_otp = data.get("otp")

    record = otp_store.get(email)

    if not record:
        return jsonify({"error": "No OTP found"}), 400

    if time.time() > record["expiry"]:
        otp_store.pop(email, None)
        return jsonify({"error": "OTP expired"}), 400

    if record["otp"] != user_otp:
        return jsonify({"error": "Invalid OTP"}), 400

    otp_verified_users.add(email)
    otp_store.pop(email, None)

    return jsonify({"message": "OTP verified"}), 200

@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if email not in otp_verified_users:
        return jsonify({"error": "OTP not verified"}), 403

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    try:
        conn = sqlite3.connect("auth.db")
        c = conn.cursor()
        c.execute(
            "INSERT INTO users_auth (email, password_hash) VALUES (?, ?)",
            (email, password_hash)
        )
        conn.commit()
        conn.close()

        otp_verified_users.remove(email)

        return jsonify({"message": "User registered successfully"}), 201

    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400

@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    conn = sqlite3.connect("auth.db")
    c = conn.cursor()

    c.execute(
        "SELECT id, password_hash FROM users_auth WHERE email=?",
        (email,)
    )

    user = c.fetchone()

    if user and bcrypt.check_password_hash(user[1], password):
        c.execute(
            "UPDATE users_auth SET last_login=? WHERE id=?",
            (datetime.datetime.utcnow(), user[0])
        )
        conn.commit()
        conn.close()

        return jsonify({"message": "Login successful", "redirect": "/chatbot"}), 200

    conn.close()
    return jsonify({"error": "Invalid email or password"}), 401

@app.route("/chat", methods=["POST"])
def chat():
    global chat_history
    global LAST_QUERY_CONTEXT

    try:
        data = request.get_json()
        user_message = str(data.get("message", "")).strip()

        if not user_message:
            return jsonify({"response": "Please enter a legal question."}), 400

        detected_lang = detect_language(user_message)
        english_message = translate_to_english(user_message, detected_lang)

        enhanced_message = enrich_followup_query(english_message)
        response_en = chatbot_response(enhanced_message)
        topic = extract_topic(english_message)

        if topic:
            LAST_QUERY_CONTEXT["query"] = english_message
            LAST_QUERY_CONTEXT["topic"] = topic

        final_response = translate_from_english(response_en, detected_lang)

        chat_history.append({
            "user": user_message,
            "response": final_response
        })

        if len(chat_history) > 20:
            chat_history = chat_history[-20:]

        return jsonify({
            "response": final_response,
            "detected_language": detected_lang,
            "enhanced_query": enhanced_message
        })

    except Exception as e:
        return jsonify({"response": "Something went wrong.", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)