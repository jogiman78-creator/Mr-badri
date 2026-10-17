import os
import sqlite3
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = os.environ.get("TELEGRAM_ADMIN_ID", "8989608134")
DB = "/var/data/submissions.db" if os.path.isdir("/var/data") else "submissions.db"

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute("CREATE TABLE IF NOT EXISTS submissions (upi TEXT PRIMARY KEY)")

init_db()

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/submit", methods=["POST"])
def submit():
    upi = request.form.get("upi", "").strip().lower()
    uid = request.form.get("uid", "").strip()
    screenshot = request.files.get("screenshot")

    if not upi or not uid or not screenshot:
        return jsonify(success=False, message="UPI, UID aur screenshot bharo."), 400

    try:
        with sqlite3.connect(DB) as con:
            con.execute("INSERT INTO submissions (upi) VALUES (?)", (upi,))
    except sqlite3.IntegrityError:
        return jsonify(success=False, message="Ye UPI ID pehle submit ho chuki hai."), 409

    if not TOKEN:
        with sqlite3.connect(DB) as con:
            con.execute("DELETE FROM submissions WHERE upi=?", (upi,))
        return jsonify(success=False, message="Server token missing."), 500

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={"chat_id": ADMIN_ID, "caption": f"New submission\nUPI: {upi}\nUID: {uid}"},
            files={"photo": (screenshot.filename, screenshot.stream, screenshot.mimetype)},
            timeout=25
        )
        r.raise_for_status()
        if not r.json().get("ok"):
            raise Exception("Telegram send failed")
    except Exception:
        with sqlite3.connect(DB) as con:
            con.execute("DELETE FROM submissions WHERE upi=?", (upi,))
        return jsonify(success=False, message="Telegram send nahi hua. Dobara baad mein try karo."), 502

    return jsonify(success=True, message="Submission received!")

if __name__ == "__main__":
    app.run()
