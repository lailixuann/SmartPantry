from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Detection(db.Model):  
    __tablename__ = 'detections'

    id = db.Column(db.Integer, primary_key=True)  
    class_name = db.Column(db.String(50))  
    confidence = db.Column(db.Float)  
    timestamp = db.Column(db.DateTime, server_default=db.func.current_timestamp())  
    is_removed = db.Column(db.Boolean, default=False) 

    __tablename__ = 'detections'

    def __repr__(self):  
        return f"<Detection(class_name='{self.class_name}', confidence={self.confidence})>"  
    
class Recipe(db.Model):
    __tablename__ = 'recipe'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    steps = db.Column(db.Text)

class RecipeIngredient(db.Model):
    __tablename__ = 'recipe_ingredient'

    id = db.Column(db.Integer, primary_key=True)
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    ingredient_name = db.Column(db.String(50), nullable=False)

    recipe = db.relationship("Recipe", backref="ingredients")