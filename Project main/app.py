from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import sqlite3
from flask_bcrypt import Bcrypt
import os
import random
import time
import datetime
import smtplib
from email.message import EmailMessage

# chatbot logic
from scripts.chatbot import handle_query


app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)

# ================= SMTP CONFIG =================

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


# ================= DATABASE =================

def init_auth_db():
    conn = sqlite3.connect("auth.db", timeout=10)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS users_auth (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_verified INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        last_login DATETIME
    )
    """)

    conn.commit()
    conn.close()


init_auth_db()


# ================= OTP STORAGE =================

otp_store = {}

def send_otp_email(to_email, otp):

    if not SMTP_USER or not SMTP_PASS:
        raise RuntimeError("SMTP credentials missing")

    msg = EmailMessage()
    msg["Subject"] = "Your LawBot OTP Code"
    msg["From"] = SMTP_FROM
    msg["To"] = to_email

    msg.set_content(
        f"Your OTP is {otp}\n"
        "It expires in 5 minutes.\n\n"
        "If you did not request this, ignore this email."
    )

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


# ================= BASIC ROUTES =================

@app.route("/")
def home():
    return render_template("chat.html")


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Backend is running"})


# ================= OTP ROUTES =================

@app.route("/send-otp", methods=["POST"])
def send_otp():

    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email required"}), 400

    otp = random.randint(100000, 999999)

    try:
        send_otp_email(email, otp)
    except Exception as e:
        print("OTP email error:", e)
        return jsonify({"error": "Failed to send OTP"}), 500

    otp_store[email] = {
        "otp": otp,
        "timestamp": time.time()
    }

    return jsonify({"message": "OTP sent successfully"})


@app.route("/verify-otp", methods=["POST"])
def verify_otp():

    data = request.json
    email = data.get("email")
    user_otp = data.get("otp")

    if not email or not user_otp:
        return jsonify({"error": "Email and OTP required"}), 400

    record = otp_store.get(email)

    if not record:
        return jsonify({"error": "No OTP found"}), 400

    if time.time() - record["timestamp"] > 300:
        return jsonify({"error": "OTP expired"}), 400

    if str(record["otp"]) == str(user_otp):
        otp_store.pop(email)
        return jsonify({"message": "OTP verified successfully"})

    return jsonify({"error": "Invalid OTP"}), 400


# ================= AUTH ROUTES =================

@app.route("/signup", methods=["POST"])
def signup():

    data = request.json
    email = data.get("email")
    password = data.get("password")

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

        return jsonify({"message": "Login successful"}), 200

    conn.close()

    return jsonify({"error": "Invalid email or password"}), 401


# ================= CHATBOT =================

chat_history = []

@app.route("/chat", methods=["POST"])
def chat():

    global chat_history

    data = request.json
    user_message = data.get("message")
    language = data.get("language")

    if not user_message:
        return jsonify({"error": "Message required"}), 400

    try:

        response, chat_history = handle_query(
            user_message,
            chat_history,
            language
        )

        return jsonify({"response": response})

    except Exception as e:

        print("Chat error:", e)

        return jsonify({
            "error": "Chatbot failed"
        }), 500


# ================= RUN SERVER =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
