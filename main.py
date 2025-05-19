import firebase_admin as fa
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import os
from flask_cors import CORS
from flask import Flask, request, jsonify, make_response

app = Flask(__name__)
CORS(app, supports_credentials=True)

cred = credentials.Certificate(".idea\ServiceAccountKey.json")
fa.initialize_app(cred)

db = firestore.client()

load_dotenv(dotenv_path=".idea/.env")

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if not email.endswith("@gmail.com"):
        return jsonify({"error": "Invalid email format. Only @gmail.com allowed."}), 400
    if len(password) < 8:
        return jsonify({"error": "Password length must be at least 8 characters."}), 400

    try:
        all_users = auth.list_users().users
        for user in all_users:
            if user.display_name == name:
                return jsonify({"error": "Username already exists"}), 409
            if user.email == email:
                return jsonify({"error": "Email already registered"}), 409

        user = auth.create_user(email=email, password=password, display_name=name)
        return jsonify({
            "message": "User registered successfully",
            "uid": user.uid,
            "email": user.email
        }), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/login", methods=["POST"])
def login():
    import requests

    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    api_key = os.getenv('API_KEY')
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    response = requests.post(url, json=payload)

    if response.status_code == 200:
        result = response.json()
        id_token = result.pop("idToken", None)

        response_data = {
            "message": "Login successful",
            "token": id_token
        }

        flask_response = make_response(jsonify(response_data), 200)

        return flask_response
    else:
        return jsonify({"error": response.json()}), 401

@app.route("/user/<uid>", methods=["GET"])
def get_user(uid):
    try:
        user = auth.get_user(uid)
        return jsonify({
            "uid": user.uid,
            "email": user.email,
            "name": user.display_name
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 404

if __name__ == "__main__":
    app.run(debug=True)
