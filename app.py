import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, messaging
import requests

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

app = Flask(__name__)

# ------------------------------------------------------
#  Firebase Admin – Inizializzazione sicura (Render)
# ------------------------------------------------------
firebase_key_json = os.environ.get("FIREBASE_KEY")

if firebase_key_json:
    # Render: la private key contiene \n, vanno convertiti in newline reali
    key_dict = json.loads(firebase_key_json)
    if "private_key" in key_dict:
        key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")

    cred = credentials.Certificate(key_dict)
    firebase_admin.initialize_app(cred)

else:
    # Locale: usa il file serviceAccountKey.json
    if os.path.exists("serviceAccountKey.json"):
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred)
    else:
        raise Exception("Nessuna chiave Firebase trovata: né FIREBASE_KEY né serviceAccountKey.json!")


# ------------------------------------------------------
#  Endpoint API per inviare una notifica a un token
# ------------------------------------------------------
@app.route("/send_notification", methods=["POST"])
def send_notification():
    data = request.json

    token = data.get("token")
    title = data.get("title", "Nuova notifica")
    body = data.get("body", "")

    if not token:
        return jsonify({"error": "Token mancante"}), 400

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(
            title=title,
            body=body,
        ),
    )

    try:
        response = messaging.send(message)
        return jsonify({"success": True, "response": response})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/", methods=["GET"])
def home():
    return "Backend FCM attivo! 🎉"

@app.route("/send_notification_group", methods=["POST"])
def send_notification_group():
    data = request.json

    vacanza_id = data.get("vacanza_id")
    title = data.get("title", "Nuova notifica")
    body = data.get("body", "")

    if not vacanza_id:
        return jsonify({"error": "vacanza_id mancante"}), 400

    # ---------------------------------------------------
    # 1) Recupera gli user_id dei partecipanti
    # ---------------------------------------------------
    headers = {
        "apikey": SUPABASE_SERVICE_KEY,
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}"
    }

    url_partecipanti = (
        f"{SUPABASE_URL}/rest/v1/vacanza_partecipanti"
        f"?vacanza_id=eq.{vacanza_id}&select=user_id"
    )

    r = requests.get(url_partecipanti, headers=headers)
    if r.status_code != 200:
        return jsonify({"error": "Errore Supabase partecipanti", "detail": r.text}), 500

    partecipanti = r.json()
    user_ids = [p["user_id"] for p in partecipanti if p.get("user_id")]

    if not user_ids:
        return jsonify({"success": True, "tokens_sent": 0})

    # ---------------------------------------------------
    # 2) Recupera i token da tokens_dispositivi
    # ---------------------------------------------------
    tokens = []

    for uid in user_ids:
        url_tokens = (
            f"{SUPABASE_URL}/rest/v1/tokens_dispositivi"
            f"?user_id=eq.{uid}&select=fcm_token"
        )
        r2 = requests.get(url_tokens, headers=headers)

        if r2.status_code == 200:
            for t in r2.json():
                token = t.get("fcm_token")
                if token:
                    tokens.append(token)

    if not tokens:
        return jsonify({"success": True, "tokens_sent": 0})

    # ---------------------------------------------------
    # 3) Invia MULTICAST a tutti i token
    # ---------------------------------------------------
    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(
            title=title,
            body=body
        ),
    )

    try:
        response = messaging.send_multicast(message)
        return jsonify({
            "success": True,
            "tokens_sent": len(tokens),
            "response": response.__dict__
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
