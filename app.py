import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, messaging

app = Flask(__name__)

# ------------------------------------------------------
#  Firebase Admin – Inizializzazione sicura (Render)
# ------------------------------------------------------
# Su Render la chiave verrà passata come variabile di ambiente "FIREBASE_KEY"
firebase_key_json = os.environ.get("FIREBASE_KEY")

if firebase_key_json:
    cred = credentials.Certificate(json.loads(firebase_key_json))
    firebase_admin.initialize_app(cred)
else:
    # Modalità locale: usa il file serviceAccountKey.json
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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
