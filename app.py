import os
import sqlite3
import requests
from flask import Flask, request, jsonify, send_file
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN_ID = os.environ.get("TELEGRAM_ADMIN_ID", "8989608134")
DB_FILE = os.environ.get("DB_PATH", "submissions.db")


def init_db():
    with sqlite3.connect(DB_FILE) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                upi TEXT PRIMARY KEY,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


init_db()


@app.route("/")
def home():
    if os.path.exists("index.html"):
        return send_file("index.html")
    return "Mr Badri website is running."


@app.route("/submit", methods=["POST"])
def submit():
    upi = (
        request.form.get("upi")
        or request.form.get("upi_id")
        or request.form.get("upiId")
        or ""
    ).strip().lower()

    uid = (
        request.form.get("uid")
        or request.form.get("game_uid")
        or ""
    ).strip()

    screenshot = (
        request.files.get("screenshot")
        or request.files.get("file")
    )

    if not upi or not uid or not screenshot:
        return jsonify({
            "success": False,
            "message": "UPI ID, UID aur screenshot zaroori hain."
        }), 400

    if "@" not in upi or len(upi) > 100:
        return jsonify({
            "success": False,
            "message": "Valid UPI ID enter karo."
        }), 400

    if not screenshot.filename:
        return jsonify({
            "success": False,
            "message": "Screenshot select karo."
        }), 400

    allowed = {"png", "jpg", "jpeg", "webp"}
    ext = screenshot.filename.rsplit(".", 1)[-1].lower()

    if "." not in screenshot.filename or ext not in allowed:
        return jsonify({
            "success": False,
            "message": "JPG, PNG ya WEBP screenshot upload karo."
        }), 400

    image_data = screenshot.read()

    if not image_data or len(image_data) > 5 * 1024 * 1024:
        return jsonify({
            "success": False,
            "message": "Screenshot khali hai ya 5 MB se bada hai."
        }), 400

    # Ek UPI ID ki sirf ek submission allow hogi.
    try:
        with sqlite3.connect(DB_FILE, timeout=10) as con:
            con.execute(
                "INSERT INTO submissions (upi) VALUES (?)",
                (upi,)
            )
    except sqlite3.IntegrityError:
        return jsonify({
            "success": False,
            "message": "Ye UPI ID pehle hi submit ho chuki hai."
        }), 409
    except sqlite3.Error:
        return jsonify({
            "success": False,
            "message": "Database error. Dobara baad mein try karo."
        }), 500

    if not TOKEN:
        with sqlite3.connect(DB_FILE) as con:
            con.execute("DELETE FROM submissions WHERE upi = ?", (upi,))
        return jsonify({
            "success": False,
            "message": "Server configuration error."
        }), 500

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendPhoto",
            data={
                "chat_id": ADMIN_ID,
                "caption": f"New submission\nUPI: {upi}\nUID: {uid}"
            },
            files={
                "photo": (
                    secure_filename(screenshot.filename),
                    image_data,
                    screenshot.mimetype or "image/jpeg"
                )
            },
            timeout=30
        )
        response.raise_for_status()

        if not response.json().get("ok"):
            raise RuntimeError("Telegram rejected the submission")

    except Exception:
        with sqlite3.connect(DB_FILE) as con:
            con.execute("DELETE FROM submissions WHERE upi = ?", (upi,))
        return jsonify({
            "success": False,
            "message": "Submission send nahi hui. Thodi der baad try karo."
        }), 502

    return jsonify({
        "success": True,
        "message": "Submission successfully received."
    })


@app.errorhandler(413)
def too_large(error):
    return jsonify({
        "success": False,
        "message": "Screenshot 5 MB se chhota hona chahiye."
    }), 413


if __name__ == "__main__":
    app.run()
