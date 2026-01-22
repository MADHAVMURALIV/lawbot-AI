from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from flask_bcrypt import Bcrypt
import google.generativeai as genai
import os
import random
import time

app = Flask(__name__)
CORS(app)  # allow frontend requests
bcrypt = Bcrypt(app)

# ================= INIT DATABASE =================
def init_db():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                first_name TEXT,
                last_name TEXT,
                email TEXT UNIQUE,
                phone TEXT,
                password TEXT)''')
    conn.commit()
    conn.close()

init_db()

# Temporary OTP storage
otp_store = {}  # {email: {"otp": 123456, "timestamp": 1690000000}}

# ================= TEST ROUTE =================
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"message": "Backend is running!"}), 200

# ================= OTP ROUTES =================
@app.route("/send-otp", methods=["POST"])
def send_otp():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    otp = random.randint(100000, 999999)
    otp_store[email] = {"otp": otp, "timestamp": time.time()}

    print(f"OTP for {email} is {otp}")  # TODO: integrate email/SMS

    return jsonify({"message": "OTP sent successfully"}), 200


@app.route("/verify-otp", methods=["POST"])
def verify_otp():
    data = request.json
    email = data.get("email")
    user_otp = data.get("otp")

    if not email or not user_otp:
        return jsonify({"error": "Email and OTP are required"}), 400

    record = otp_store.get(email)
    if not record:
        return jsonify({"error": "No OTP found for this email"}), 400

    if time.time() - record["timestamp"] > 300:
        return jsonify({"error": "OTP expired"}), 400

    if str(record["otp"]) == str(user_otp):
        otp_store.pop(email)
        return jsonify({"message": "OTP verified successfully"}), 200
    else:
        return jsonify({"error": "Invalid OTP"}), 400

# ================= AUTH ROUTES =================
@app.route("/signup", methods=["POST"])
def signup():
    data = request.json
    hashed_pw = bcrypt.generate_password_hash(data["password"]).decode("utf-8")

    try:
        conn = sqlite3.connect("users.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (first_name, last_name, email, phone, password) VALUES (?, ?, ?, ?, ?)",
                  (data["first_name"], data["last_name"], data["email"], data["phone"], hashed_pw))
        conn.commit()
        conn.close()
        return jsonify({"message": "User registered successfully"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password FROM users WHERE email=?", (data["email"],))
    row = c.fetchone()
    conn.close()

    if row and bcrypt.check_password_hash(row[0], data["password"]):
        return jsonify({"message": "Login successful"}), 200
    return jsonify({"error": "Invalid email or password"}), 401


# ================= CHATBOT ROUTE =================
# configure Gemini API
API_KEY = "AIzaSyA7C0KTO5l9eB3oxvtzhc2b7erEK-y58OA"  # API KEY 
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message")
    history = data.get("history", [])

    if not user_input:
        return jsonify({"error": "Message is required"}), 400

    try:
        messages = "".join([f"User: {u}\nBot: {b}\n" for u, b in history])
        full_prompt = (
            "You are a helpful multilingual chatbot. "
            "Always reply in the same language as the user.\n\n"
            f"{messages}\nUser: {user_input}"
        )

        response = model.generate_content(full_prompt)
        bot_reply = response.text.strip() if response and response.text else "Sorry, I couldn't generate a response."

        history.append((user_input, bot_reply))
        return jsonify({"reply": bot_reply, "history": history})

    except Exception as e:
        print("Error:", e)
        return jsonify({"error": "Internal server error"}), 500


# ================= RUN APP =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


















