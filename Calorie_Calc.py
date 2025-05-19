from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
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

@app.route("/calculateCalories", methods=["POST"])
def calculate_calories():
    data = request.get_json()
    food_name = data.get("food_name")
    quantity = data.get("quantity")

    if not food_name or not quantity:
        return jsonify({"error": "Food name and quantity must not be empty."}), 400

    try:
        quantity = float(quantity)
    except ValueError:
        return jsonify({"error": "Quantity must be a number."}), 400

    # Fetch food data from Firestore where food_name matches
    food_docs = db.collection("FoodList").where("food_name", "==", food_name).stream()
    food_doc = next(food_docs, None)

    if not food_doc:
        return jsonify({"error": "Food not found"}), 404

    food_data = food_doc.to_dict()

    # Calculate based on per 100g
    calories = food_data.get("calories", 0) * quantity / 100
    carbs = food_data.get("carbohydrates", 0) * quantity / 100
    proteins = food_data.get("proteins", 0) * quantity / 100
    fats = food_data.get("fats", 0) * quantity / 100

    return jsonify({
        "calculated": {
            "calories": round(calories, 2),
            "carbohydrates": round(carbs, 2),
            "proteins": round(proteins, 2),
            "fats": round(fats, 2)
        }
    }), 200

if __name__ == '__main__':
    app.run(debug=True)