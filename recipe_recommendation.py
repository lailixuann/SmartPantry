from app import app, db, get_db_items
import csv
import pandas as pd
from sqlalchemy import func
from db_models import Recipe, RecipeIngredient

def recommend_recipes(pantry_items):
    matched_counts = db.session.query(
        RecipeIngredient.recipe_id,
        func.count().label("matched")
    ).filter(
        RecipeIngredient.ingredient_name.in_(pantry_items)
    ).group_by(
        RecipeIngredient.recipe_id
    ).subquery()

    query = db.session.query(
        Recipe,
        matched_counts.c.matched,
        func.count(RecipeIngredient.id).label("total")
    ).join(RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id)\
     .outerjoin(matched_counts, Recipe.id == matched_counts.c.recipe_id)\
     .group_by(Recipe.id, matched_counts.c.matched)\
     .order_by(
         db.case(
             (matched_counts.c.matched == None, 1),
             else_ = 0
         ),
        matched_counts.c.matched.desc()
     )

    results = query.all()
    return [(r, m, t) for r, m, t in results if m is not None and m > 0]

    # scored = []
    # for recipe in recipes:
    #     match_count = sum(1 for item in recipe['ingredients'] if item in pantry_items)
    #     scored.append({
    #         'name': recipe['name'],
    #         'matched': match_count,
    #         'total': len(recipe['ingredients']),
    #         'missing': list(set(recipe['ingredients']) - set(pantry_items))
    #     })

    # # Sort by matched count descending, then recipe name
    # scored.sort(key=lambda x: (-x['matched'], x['name']))
    # return scored

if __name__ == "__main__":
    with app.app_context():
        pantry_items = get_db_items()
        results = recommend_recipes(pantry_items)
        for recipe, matched, total in results:
            print(f"Recipe: {recipe.name}, Matched: {matched}, Total: {total}")