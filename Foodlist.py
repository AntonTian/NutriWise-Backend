from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
from dotenv import load_dotenv
import os
from flask_cors import CORS

# Initialize Firebase
app = Flask(__name__)
CORS(app, supports_credentials=True)

cred = credentials.Certificate(".idea\ServiceAccountKey.json")
initialize_app(cred)

db = firestore.client()

load_dotenv(dotenv_path=".idea/.env")

# Ensure user exists with a food list
def ensure_user_foodlist(username):
    user_ref = db.collection("UserFoodLists").document(username)
    if not user_ref.get().exists:
        user_ref.set({"foods": []})
    return user_ref

# Get food list based on username from request body
@app.route('/getFoodlistBasedUser', methods=['POST'])
def get_foodlist_based_user():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    user_ref = ensure_user_foodlist(username)
    foods = user_ref.get().to_dict().get("foods", [])
    filtered_foods = [f for f in foods if not f.get("isDeleted", False)]
    return jsonify(filtered_foods), 200

# Add a new food item
@app.route('/addFood', methods=['POST'])
def add_food():
    data = request.get_json()
    required_fields = ['username', 'food_name', 'quantity', 'expiry_date']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Please Fill all the fields before adding!"}), 400

    username = data["username"]
    user_ref = ensure_user_foodlist(username)
    foods = user_ref.get().to_dict().get("foods", [])

    for food in foods:
        if food["food_name"].lower() == data["food_name"].strip().lower() and not food.get("isDeleted", False):
            return jsonify({"error": "Food already exists"}), 400

    try:
        expiry_date = datetime.strptime(data["expiry_date"], "%Y-%m-%d")
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    new_food = {
        "food_name": data['food_name'].strip().title(),
        "quantity": int(data['quantity']),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "isDeleted": False
    }

    user_ref.update({"foods": firestore.ArrayUnion([new_food])})
    updated_foods = user_ref.get().to_dict().get("foods", [])
    return jsonify(updated_foods), 201

#delete food item
@app.route('/DeleteFood', methods=['PATCH'])
def delete_food():
    data = request.get_json()
    required_fields = ['username', 'food_name', 'quantity', 'expiry_date']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400

    username = data["username"]
    user_ref = ensure_user_foodlist(username)
    foods = user_ref.get().to_dict().get("foods", [])

    updated = False
    for food in foods:
        if (food["food_name"].lower() == data["food_name"].strip().lower() and
            str(food["quantity"]) == str(data["quantity"]) and
            food["expiry_date"] == data["expiry_date"] and
            not food.get("isDeleted", False)):
            food["isDeleted"] = True
            updated = True
            break

    if not updated:
        return jsonify({"error": "Matching food not found"}), 404

    user_ref.update({"foods": foods})
    return jsonify({"message": f"Food '{data['food_name']}' deleted"}), 200

if __name__ == '__main__':
    app.run(debug=True)