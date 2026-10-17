import os
import sqlite3
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = os.environ.get("TELEGRAM_ADMIN_ID", "8989608134")
DB = "submissions.db"


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

    if not upi or not uid or not screenshot or not screenshot.filename:
        return jsonify(success=False, message="UPI, UID aur screenshot bharo."), 400

    if not TOKEN:
        return jsonify(success=False, message="Telegram bot token missing hai."), 500

    try:
        with sqlite3.connect(DB, timeout=10) as con:
            con.execute("INSERT INTO submissions (upi) VALUES (?)", (upi,))
    except sqlite3.IntegrityError:
        return jsonify(success=False, message="Ye UPI ID pehle submit ho chuki hai."), 409

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={
                "chat_id": ADMIN_ID,
                "caption": f"New submission\nUPI: {upi}\nUID: {uid}"
            },
            files={
                "photo": (
                    screenshot.filename,
                    screenshot.stream,
                    screenshot.mimetype or "image/jpeg"
                )
            },
            timeout=25
        )
        response.raise_for_status()

        if not response.json().get("ok"):
            raise RuntimeError("Telegram rejected submission")

    except Exception:
        with sqlite3.connect(DB) as con:
            con.execute("DELETE FROM submissions WHERE upi=?", (upi,))
        app.logger.exception("Telegram submission failed")
        return jsonify(success=False, message="Telegram send nahi hua. Logs check karo."), 502

    return jsonify(success=True, message="Submission received!")


@app.errorhandler(413)
def too_large(error):
    return jsonify(success=False, message="Screenshot 5 MB se chhota hona chahiye."), 413
