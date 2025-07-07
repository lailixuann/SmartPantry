from app import app, db, get_db_items
from sqlalchemy import func
from db_models import Detection, Recipe, RecipeIngredient

ingredients_dict = {
    'beef':['beef','ground beef','minced beef','boneless beef chuck','beef steak','oxtail','lean beef','stewing beef'],
    'cabbage':['cabbage','chinese cabbage', 'green cabbage'],
    'chicken':['chicken','chicken breasts','chicken breast','boneless skinless chicken breasts','boneless skinless chicken breast','boneless skinless chicken thighs','skinless chicken thighs','chicken thighs','chicken thigh fillets','chicken legs-thighs','roasting chicken','chicken piece','chicken wings','whole chickens','minced chicken','chicken legs','chicken cutlet','chicken parts','cooked chicken','chicken breast halves','roasting chickens','chicken pieces','minced chicken',],
    'chili_pepper':['chili pepper','chili peppers','dried chilies','fresh chili peppers','hot chili pepper','dried hot chili peppers','hot green chili pepper','green chili pepper','hot red chili peppers','red chili peppers','red chili pepper','thai red chili peppers','dried chili pepper flakes','red chili pepper flakes'],
    'cilantro':['cilantro','fresh cilantro','fresh cilantro leaves','fresh cilantro stem'],
    'egg':['egg','eggs','egg white','egg yolk','egg yolks','hard-boiled eggs'],
    'fish':['fish','fish fillet','fish fillets','white fish fillets'],
    'garlic':['garlic','garlic clove','garlic cloves','fresh garlic','fresh garlic cloves','garlic juice','garlic granules'],
    'ginger':['ginger','fresh ginger','minced ginger','ground ginger','ginger juice','gingerroot','preserved gingerroot','fresh gingerroot','crystallized ginger'],
    'green_onion':['green onion','green onions','spring onion','spring onions'],
    'lime':['lime','limes','lime rind','lime juice','limes juice','lime slice','fresh lime juice','lime wedges','kaffir lime'],
    'mango':['mango','mangoes','green mango','green mangoes','mango pulp'],
    'noodles':['noodles','rice noodles','ramen noodles','egg noodles','hokkien noodles','wheat noodles','chinese egg noodles','thai rice noodles','dried rice noodles','cooked noodles'],
    'onion':['onion','onions','fresh onions','french-fried onions','red onion','red onions','brown onion','yellow onion','white onion','bombay onion'],
    'potato':['potato','potatoes','yukon gold potatoes'],
    'tomato':['tomato','tomatoes','chopped tomatoes','tomato puree']
}

def expand_ingredient(pantry_items):
    expanded = set()
    for item in pantry_items:
        if not item:
            continue
        variations = ingredients_dict.get(item.lower(), [])
        expanded.update(variations)
    return expanded

def recommend_recipes(pantry_items):
    pantry_items = db.session.query(Detection.class_name).filter_by(is_removed = False).all()
    pantry_items = [item[0] for item in pantry_items]

    expanded_ingredients = expand_ingredient(pantry_items)
    print("Pantry: ", pantry_items)
    print("Expanded ingredients: ", expanded_ingredients)
    
    matched_counts = db.session.query(
        RecipeIngredient.recipe_id,
        func.count().label("matched")
    ).filter(
        RecipeIngredient.ingredient_name.in_(expanded_ingredients)
    ).group_by(
        RecipeIngredient.recipe_id
    ).subquery()

    query = db.session.query(
        Recipe,
        matched_counts.c.matched
        ).join(
           RecipeIngredient, Recipe.id == RecipeIngredient.recipe_id
        ).outerjoin(
           matched_counts, Recipe.id == matched_counts.c.recipe_id
        ).group_by(
            Recipe.id, matched_counts.c.matched
        ).order_by(
         db.case(
             (matched_counts.c.matched == None, 1),
             else_ = 0
         ),
        matched_counts.c.matched.desc()
     )

    results = query.all()
    return [(r, m) for r, m in results if m is not None and m > 0]