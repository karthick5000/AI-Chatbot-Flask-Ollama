from flask import Flask, render_template, request, redirect, session, jsonify
import bcrypt
import requests

from config import SECRET_KEY
from database import get_connection, init_db

app = Flask(__name__)
app.secret_key = SECRET_KEY

init_db()

# ---------------- AI ----------------
def get_ai_response(message):
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "phi3",
                "prompt": message,
                "stream": False
            }
        )

        data = response.json()
        return data["response"]

    except Exception as e:
        return f"Ollama Error: {str(e)}"

# ---------------- ROUTES ----------------
@app.route("/")
def home():
    return redirect("/chat") if "user_id" in session else redirect("/login")

# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = bcrypt.hashpw(
            request.form["password"].encode(),
            bcrypt.gensalt()
        )

        conn = get_connection()
        cursor = conn.cursor()

        try:
            cursor.execute(
                "INSERT INTO users (username, password) VALUES (?, ?)",
                (username, password)
            )
            conn.commit()
        except:
            return "User already exists"

        conn.close()
        return redirect("/login")

    return render_template("register.html")

# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"].encode()

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id, password FROM users WHERE username=?", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and bcrypt.checkpw(password, user[1]):
            session["user_id"] = user[0]
            return redirect("/chat")

        return "Invalid credentials"

    return render_template("login.html")

# LOGOUT
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# CHAT PAGE
@app.route("/chat")
def chat():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("index.html")

# SEND MESSAGE
@app.route("/send", methods=["POST"])
def send():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"})

    message = request.json["message"]
    response = get_ai_response(message)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO chats (user_id, message, response) VALUES (?, ?, ?)",
        (session["user_id"], message, response)
    )

    conn.commit()
    conn.close()

    return jsonify({"response": response})

# HISTORY
@app.route("/history")
def history():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT message, response FROM chats WHERE user_id=?",
        (session["user_id"],)
    )

    data = cursor.fetchall()
    conn.close()

    return jsonify(data)

# RUN
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)