'''run once only to import recipes into database'''
from db_models import db, Recipe, RecipeIngredient
import csv
from app import app
import json

with open('final_recipes.csv', newline='', encoding='utf-8') as f:
    with app.app_context():
        reader = csv.DictReader(f)
        for row in reader:
            steps = row['steps']
            try:
                # Safely evaluate the string to a list (e.g., from "['step1', 'step2']" to list)
                steps_list = eval(steps)
                if isinstance(steps_list, list):
                    steps_json = json.dumps(steps_list)  # Properly formatted JSON string
                else:
                    steps_json = json.dumps([])
            except:
                steps_json = json.dumps([])

            recipe = Recipe(name=row['name'],
                            description=row['description'],
                            steps=steps_json
                            )
            db.session.add(recipe)
            db.session.flush()

            ingredients = [i.strip() for i in row['ingredients'].split(',')]
            for ing in ingredients:
                db.session.add(RecipeIngredient(recipe_id=recipe.id, ingredient_name=ing))
        db.session.commit()