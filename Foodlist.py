from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
from datetime import datetime
from dotenv import load_dotenv
import os
from flask_cors import CORS
from uuid import uuid4

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

# Get all foodnames (Need to fix)
@app.route("/getAllFoodNames", methods=["GET"])
def get_all_food_names():
    try:
        food_names = []

        food_docs = db.collection("FoodList").stream()

        for doc in food_docs:
            food_data = doc.to_dict()
            name = food_data.get("food_name")
            if name:
                food_names.append(name)

        return jsonify(sorted(set(food_names))), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# Get food list based on username from request body
@app.route('/getFoodlistBasedUser', methods=['POST'])
def get_foodlist_based_user():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    user_ref = ensure_user_foodlist(username)
    foods = user_ref.get().to_dict().get("foods", [])
    filtered_foods = [
        {
            "log_id": food["log_id"],
            "food_name": food["food_name"],
            "quantity": food["quantity"],
            "expiry_date": food["expiry_date"]
        }
        for food in foods if not food.get("isDeleted", False)
    ]
    return jsonify(filtered_foods), 200

# Add a new food item
@app.route('/addFood', methods=['POST'])
def add_food():
    data = request.get_json()
    required_fields = ['username', 'food_name', 'quantity', 'expiry_date']
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Please Fill all the fields before adding!"}), 400

    username = data["username"]

    # 🔍 Lookup UID from Firestore "Users" collection
    user_meta = db.collection("Users").document(username).get()
    if not user_meta.exists:
        return jsonify({"error": "User not found"}), 404

    user_id = user_meta.to_dict().get("uid")  # UID from Firebase Auth

    raw_food_name = data["food_name"]
    normalized_food_name = raw_food_name.replace("-", " ").strip().title()

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
        "log_id": str(uuid4()),
        "food_name": normalized_food_name,
        "quantity": str(data['quantity']),
        "expiry_date": expiry_date.strftime("%Y-%m-%d"),
        "isDeleted": False
    }

    user_ref.update({"foods": firestore.ArrayUnion([new_food])})

    # 🔍 Log the action with UID
    db.collection("FoodLogs").add({
        "log_id": str(uuid4()),
        "user_id": user_id,
        "food_name": normalized_food_name,
        "quantity": new_food["quantity"],
        "expiry_date": new_food["expiry_date"],
        "date_up": firestore.SERVER_TIMESTAMP,
        "isDeleted": False
    })

    updated_foods = user_ref.get().to_dict().get("foods", [])
    return jsonify(updated_foods), 201

#delete food item
@app.route('/DeleteFood', methods=['PATCH'])
def delete_food():
    data = request.get_json()
    if "username" not in data or "log_id" not in data:
        return jsonify({"error": "Missing required fields: username and log_id"}), 400

    username = data["username"]
    log_id = data["log_id"]

    # Get reference to the user's food list
    user_ref = ensure_user_foodlist(username)
    user_doc = user_ref.get()

    if not user_doc.exists:
        return jsonify({"error": "User food list not found"}), 404

    user_data = user_doc.to_dict() or {}
    foods = user_data.get("foods", [])

    updated = False

    for food in foods:
        # Ensure food has a log_id before comparing
        if str(food.get("log_id")) == str(log_id) and not food.get("isDeleted", False):
            food["isDeleted"] = True
            updated = True

            # Log the deletion to FoodLogs
            db.collection("FoodLogs").add({
                "log_id": log_id,
                "user_id": username,
                "food_name": food.get("food_name", ""),
                "quantity": food.get("quantity", ""),
                "expiry_date": food.get("expiry_date", ""),
                "date_up": firestore.SERVER_TIMESTAMP,
                "isDeleted": True,
            })
            break

    if not updated:
        return jsonify({"error": "No matching food found with provided log_id"}), 404

    # Save updated food list
    user_ref.update({"foods": foods})

    return jsonify({"message": f"Food with log_id '{log_id}' marked as deleted."}), 200

@app.route("/test-food", methods=["POST"])
def test_food_lookup():
    data = request.get_json()
    food_name = data.get("food_name")

    if not food_name:
        return jsonify({"error": "Missing food_name"}), 400

    food_docs = db.collection("FoodList").where("food_name", "==", food_name).stream()
    food_doc = next(food_docs, None)

    if not food_doc:
        return jsonify({"error": "Food not found"}), 404

    return jsonify(food_doc.to_dict()), 200

if __name__ == '__main__':
    app.run(debug=True)