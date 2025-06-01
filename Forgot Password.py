import firebase_admin as fa
from firebase_admin import credentials, firestore, auth
from dotenv import load_dotenv
import os
from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_mail import Mail, Message
import random
import time


app = Flask(__name__)
CORS(app, supports_credentials=True)

cred = credentials.Certificate(".idea\ServiceAccountKey.json")
fa.initialize_app(cred)

db = firestore.client()

load_dotenv(dotenv_path=".idea/.env")

#Forgot and reset password
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'nutriwiseee@gmail.com'
app.config['MAIL_PASSWORD'] = 'aion jsyc pagr bkwz'
app.config['MAIL_DEFAULT_SENDER'] = ("Nutriwise Support", "nutriwiseee@gmail.com")

mail = Mail(app)

# In-memory store (replace with Firestore or Redis for production)
verification_codes = {}

def generate_verification_code():
    return str(random.randint(100000, 999999))

def send_verification_email(email, code):
    try:
        msg = Message(
            subject="Your Verification Code",
            recipients=[email],
            html=f"<strong>Your verification code is: {code}</strong>"
        )
        mail.send(msg)
        print(f"[DEBUG] Sent code {code} to {email}")
        return True
    except Exception as e:
        print(f"[ERROR] Failed to send email to {email}: {e}")
        return False

@app.route('/requestResetCode', methods=['POST'])
def request_reset_code():
    data = request.json
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    try:
        auth.get_user_by_email(email)
    except auth.UserNotFoundError:
        return jsonify({"error": "No user found with that email"}), 404

    code = generate_verification_code()
    verification_codes[email] = {
        "code": code,
        "expires": time.time() + 300
    }

    if not send_verification_email(email, code):
        return jsonify({"error": "Failed to send verification code"}), 500

    return jsonify({"message": "Verification code sent to email"}), 200

@app.route('/verifyResetCode', methods=['POST'])
def verify_reset_code():
    data = request.json
    email = data.get("email")
    user_code = data.get("code")

    if not email or not user_code:
        return jsonify({"error": "Email and code are required"}), 400

    record = verification_codes.get(email)
    if not record:
        return jsonify({"error": "No reset request found for this email"}), 400

    if time.time() > record["expires"]:
        return jsonify({"error": "Verification code expired"}), 400

    if str(user_code) != record["code"]:
        return jsonify({"error": "Incorrect verification code"}), 400

    try:
        link = auth.generate_password_reset_link(email)
        return jsonify({
            "message": "Verification successful. Password reset link generated.",
            "reset_link": link
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)