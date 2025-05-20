from flask import Flask, request, jsonify
from firebase_admin import credentials, firestore, initialize_app
from dotenv import load_dotenv
import os
from flask_cors import CORS
import re 

# Initialize Firebase
app = Flask(__name__)
CORS(app, supports_credentials=True)

cred = credentials.Certificate(".idea\ServiceAccountKey.json")
initialize_app(cred)

db = firestore.client()

load_dotenv(dotenv_path=".idea/.env")

def extract_ingredient_names(ingredient_lines):
    ingredient_names = set()

    descriptors_to_ignore = {"bruised", "sliced", "grated", "minced", "thinly", "julienned", "soaked", "cut into cubes"}
    for line in ingredient_lines:
        parts = line.split(";")
        for part in parts:
            part = part.strip().lower()

            # Remove quantity and unit prefixes
            part = re.sub(r'^\d+(\.\d+)?\s*(g|gram|grams|ml|cup[s]?|tbsp[s]?|tsp[s]?|inch|clove[s]?|slice[d]?|stalk[s]?|leaves?)?\s*', '', part)

            # Normalize 'to taste'
            part = re.sub(r'\bto taste\b', '', part).strip()

            # Remove descriptors like 'bruised', 'sliced', etc.
            words = [word for word in part.split() if word not in descriptors_to_ignore]
            cleaned_part = " ".join(words).strip()

            # Final cleanup
            cleaned_part = re.sub(r'[^\w\s]', '', cleaned_part).strip()

            if cleaned_part:
                ingredient_names.add(cleaned_part)

    return ingredient_names


@app.route('/getRecipesWithAvailability', methods=['POST'])
def get_recipes_with_availability():
    data = request.json
    username = data.get("username")

    if not username:
        return jsonify({"error": "Username is required"}), 400

    # Get all user's available food items, skipping deleted ones
    user_food_docs = db.collection("UserFoodLists").document(username).get()
    if not user_food_docs.exists:
        return jsonify({"error": "User not found"}), 404

    user_food_data = user_food_docs.to_dict().get("foods", [])
    user_ingredients_map = {
        item["food_name"].strip().lower(): item["food_name"].strip()
        for item in user_food_data if not item.get("isDeleted", False)
    }
    user_ingredients_lower = set(user_ingredients_map.keys())

    recipe_docs = db.collection("FoodList").stream()
    recipes = []

    for doc in recipe_docs:
        recipe = doc.to_dict()
        title = recipe.get("recipe_title")
        steps = recipe.get("recipe_steps")
        ingredient_lines = recipe.get("ingredients", [])

        parsed_ingredients = extract_ingredient_names(ingredient_lines)

        # Case-insensitive comparison using lowercased keys
        available = [user_ingredients_map[ing] for ing in parsed_ingredients if ing in user_ingredients_lower]
        unavailable = [ing.title() for ing in parsed_ingredients if ing not in user_ingredients_lower]  # Optional: title-case

        recipes.append({
            "recipe_title": title,
            "recipe_steps": steps,
            "ingredient_details": ingredient_lines,
            "available_ingredients": available,
            "unavailable_ingredients": unavailable,
            "total_ingredients": len(parsed_ingredients)
        })

    # Sort recipes by number of ingredients (descending)
    recipes.sort(key=lambda x: x["total_ingredients"], reverse=True)
    return jsonify({"recipes": recipes}), 200

if __name__ == '__main__':
    app.run(debug=True)