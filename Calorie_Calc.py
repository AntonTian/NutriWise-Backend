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

@app.route("/calorie/add", methods=["POST"])
def add_calorie_food():
    data = request.get_json()
    username = data.get("username")
    food_name = data.get("food_name")
    quantity = data.get("quantity")

    if not all([username, food_name, quantity]):
        return jsonify({"error": "Missing required fields"}), 400

    # Get food info from FoodList collection
    food_docs = db.collection("FoodList").where("food_name", "==", food_name).stream()
    food_doc = next(food_docs, None)
    if not food_doc:
        return jsonify({"error": "Food not found"}), 404

    food_data = food_doc.to_dict()

    # Scale nutrition based on quantity
    factor = quantity / 100
    entry = {
        "food_name": food_name,
        "quantity": quantity,
        "calories": round(food_data.get("calories", 0) * factor, 2),
        "carbs": round(food_data.get("carbs", 0) * factor, 2),
        "protein": round(food_data.get("protein", 0) * factor, 2),
        "fats": round(food_data.get("fats", 0) * factor, 2)
    }

    doc_ref = db.collection("CalorieSession").document(username)
    doc = doc_ref.get()
    if doc.exists:
        current_data = doc.to_dict().get("foods", [])
        current_data.append(entry)
    else:
        current_data = [entry]

    doc_ref.set({"foods": current_data})

    return jsonify({"message": "Food added to calorie session", "foods": current_data}), 200

@app.route("/calorie/delete", methods=["POST"])
def delete_calorie_food():
    data = request.get_json()
    username = data.get("username")
    food_name = data.get("food_name")

    doc_ref = db.collection("CalorieSession").document(username)
    doc = doc_ref.get()
    if not doc.exists:
        return jsonify({"error": "No session found"}), 404

    current_foods = doc.to_dict().get("foods", [])
    updated_foods = [food for food in current_foods if food["food_name"] != food_name]

    doc_ref.set({"foods": updated_foods})
    return jsonify({"message": "Food deleted", "foods": updated_foods}), 200

@app.route("/calorie/summary", methods=["POST"])
def get_calorie_summary():
    data = request.get_json()
    username = data.get("username")

    doc = db.collection("CalorieSession").document(username).get()
    if not doc.exists:
        return jsonify({"error": "No data found"}), 404

    foods = doc.to_dict().get("foods", [])
    summary = {
        "calories": sum(f["calories"] for f in foods),
        "carbs": sum(f["carbs"] for f in foods),
        "protein": sum(f["protein"] for f in foods),
        "fats": sum(f["fats"] for f in foods)
    }

    return jsonify({
        "foods": foods,
        "summary": summary
    }), 200

if __name__ == '__main__':
    app.run(debug=True)