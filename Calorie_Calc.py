from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
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

@app.route('/getCalorieBasedUser', methods=['POST'])
def get_calorie_based_user():
    data = request.get_json()
    username = data.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    doc_ref = db.collection("CalorieSession").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "No calorie session found for this user"}), 404

    all_foods = doc.to_dict().get("foods", [])

    # Only include foods not marked as deleted
    filtered_foods = [
        {
            "log_id": food["log_id"],
            "food_name": food["food_name"],
            "quantity": food["quantity"],
            "calories": food["calories"],
            "carbs": food["carbs"],
            "protein": food["protein"],
            "fats": food["fats"]
        }
        for food in all_foods if not food.get("isDeleted", False)
    ]

    return jsonify(filtered_foods), 200


@app.route("/calorie/add", methods=["POST"])
def add_calorie_food():
    data = request.get_json()
    username = data.get("username")
    food_name = data.get("food_name")
    quantity = data.get("quantity")

    if not all([username, food_name, quantity]):
        return jsonify({"error": "Missing required fields"}), 400

    try:
        quantity = float(quantity)
    except ValueError:
        return jsonify({"error": "Quantity must be a number"}), 400

    # Get food info from FoodList collection
    food_docs = db.collection("FoodList").where("food_name", "==", food_name).stream()
    food_doc = next(food_docs, None)
    if not food_doc:
        return jsonify({"error": "Food not found"}), 404

    food_data = food_doc.to_dict()
    factor = quantity / 100

    entry = {
        "log_id": str(uuid4()),
        "food_name": food_name,
        "quantity": quantity,
        "calories": round(food_data.get("calories", 0) * factor, 2),
        "carbs": round(food_data.get("carbs", 0) * factor, 2),
        "protein": round(food_data.get("protein", 0) * factor, 2),
        "fats": round(food_data.get("fats", 0) * factor, 2),
        "isDeleted": False
    }

    doc_ref = db.collection("CalorieSession").document(username)
    doc = doc_ref.get()
    foods = doc.to_dict().get("foods", []) if doc.exists else []
    foods.append(entry)

    doc_ref.set({"foods": foods})

    return jsonify({"message": "Food added to calorie session", "foods": foods}), 200

@app.route("/calorie/delete", methods=["PATCH"])
def delete_calorie_food():
    data = request.get_json()
    username = data.get("username")
    log_id = data.get("log_id")

    if not username or not log_id:
        return jsonify({"error": "Missing username or log_id"}), 400

    doc_ref = db.collection("CalorieSession").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "No session found"}), 404

    foods = doc.to_dict().get("foods", [])
    updated = False

    for food in foods:
        if food.get("log_id") == log_id and not food.get("isDeleted", False):
            food["isDeleted"] = True
            updated = True
            break

    if not updated:
        return jsonify({"error": "No matching food found with provided log_id"}), 404

    doc_ref.set({"foods": foods})
    return jsonify({"message": f"Food with log_id '{log_id}' marked as deleted."}), 200

@app.route("/calorie/summary", methods=["POST"])
def get_calorie_summary():
    data = request.get_json()
    username = data.get("username")

    doc = db.collection("CalorieSession").document(username).get()
    if not doc.exists:
        return jsonify({"error": "No data found"}), 404

    all_foods = doc.to_dict().get("foods", [])

    # Filter out deleted foods
    active_foods = [f for f in all_foods if not f.get("isDeleted", False)]

    # summarize only non-deleted entries
    summary = {
        "calories": sum(f.get("calories", 0) for f in active_foods),
        "carbs": sum(f.get("carbs", 0) for f in active_foods),
        "protein": sum(f.get("protein", 0) for f in active_foods),
        "fats": sum(f.get("fats", 0) for f in active_foods)
    }

    return jsonify({
        "foods": active_foods,
        "summary": summary
    }), 200

if __name__ == '__main__':
    app.run(debug=True)