import os
import re
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
ADMIN = os.environ.get("TELEGRAM_ADMIN_ID", "8989608134")

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/submit", methods=["POST"])
def submit():
    if not TOKEN:
        return jsonify(error="Bot not configured"), 503

    if request.is_json:
        data = request.get_json(silent=True) or {}
        upi = str(data.get("upi", "")).strip()

        if data.get("type") != "upi":
            return jsonify(error="Invalid request"), 400

        if not re.fullmatch(r"[A-Za-z0-9._-]+@[A-Za-z0-9.-]+", upi):
            return jsonify(error="Invalid UPI ID"), 400

        text = "Mr Badri Rewards\nUPI ID: " + upi
        method = "sendMessage"
        payload = {"chat_id": ADMIN, "text": text}

    else:
        uid = str(request.form.get("uid", "")).strip()
        photo = request.files.get("proof")

        if request.form.get("type") != "uid" or not uid or not photo:
            return jsonify(error="UID and screenshot required"), 400

        if photo.mimetype not in ["image/jpeg", "image/png", "image/webp"]:
            return jsonify(error="Image only"), 400

        content = photo.read(5 * 1024 * 1024 + 1)
        if len(content) > 5 * 1024 * 1024:
            return jsonify(error="Image too large"), 400

        text = "Mr Badri Rewards\nUID: " + uid
        method = "sendPhoto"
        payload = {"chat_id": ADMIN, "caption": text}

        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TOKEN}/{method}",
                data=payload,
                files={"photo": (photo.filename, content, photo.mimetype)},
                timeout=20
            )
            r.raise_for_status()
            if not r.json().get("ok"):
                return jsonify(error="Telegram error"), 502
            return jsonify(ok=True)
        except Exception:
            return jsonify(error="Telegram send failed"), 502

    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/{method}",
            json=payload,
            timeout=20
        )
        r.raise_for_status()
        if not r.json().get("ok"):
            return jsonify(error="Telegram error"), 502
        return jsonify(ok=True)
    except Exception:
        return jsonify(error="Telegram send failed"), 502

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
