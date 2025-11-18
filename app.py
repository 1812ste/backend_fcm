import os
import json
from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, messaging

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
