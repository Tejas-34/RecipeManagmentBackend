from flask import Flask, request, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from model import User, Recipe
import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'supersecretkey'

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.objects(pk=user_id).first()


# ---------------- AUTH ROUTES ---------------- #

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.objects(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 400
    if User.objects(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400
    
    user = User(username=data["username"], email=data["email"])
    user.set_password(data["password"])
    user.save()
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.objects(username=data["username"]).first()
    if user and user.check_password(data["password"]):
        login_user(user)
        return jsonify({"message": "Logged in successfully"})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})


# ---------------- RECIPE ROUTES ---------------- #

@app.route("/recipe", methods=["POST"])
@login_required
def add_recipe():
    data = request.json
    recipe = Recipe(
        title=data["title"],
        description=data.get("description", ""),
        ingredients=data.get("ingredients", []),
        steps=data.get("steps", []),
        image_url=data.get("image_url"),
        cuisine=data.get("cuisine", "Other"),
        difficulty=data.get("difficulty", "Easy"),
        cooking_time=data.get("cooking_time", 0),
        author=current_user._get_current_object()
    )
    recipe.save()
    return jsonify({"message": "Recipe added successfully"}), 201


@app.route("/recipes", methods=["GET"])
def get_recipes():
    recipes = Recipe.objects()
    output = []
    for r in recipes:
        output.append({
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "ingredients": r.ingredients,
            "steps": r.steps,
            "image_url": r.image_url,
            "cuisine": r.cuisine,
            "difficulty": r.difficulty,
            "cooking_time": r.cooking_time,
            "author": str(r.author.username) if r.author else None,
            "created_at": r.created_at,
        })
    return jsonify(output)


@app.route("/recipe/<id>", methods=["PUT"])
@login_required
def edit_recipe(id):
    recipe = Recipe.objects(id=id, author=current_user._get_current_object()).first()
    if not recipe:
        return jsonify({"error": "Recipe not found or unauthorized"}), 404
    
    data = request.json
    recipe.update(
        title=data.get("title", recipe.title),
        description=data.get("description", recipe.description),
        ingredients=data.get("ingredients", recipe.ingredients),
        steps=data.get("steps", recipe.steps),
        image_url=data.get("image_url", recipe.image_url),
        cuisine=data.get("cuisine", recipe.cuisine),
        difficulty=data.get("difficulty", recipe.difficulty),
        cooking_time=data.get("cooking_time", recipe.cooking_time),
        updated_at=datetime.datetime.utcnow()
    )
    return jsonify({"message": "Recipe updated successfully"}), 200


@app.route("/recipe/<id>", methods=["DELETE"])
@login_required
def delete_recipe(id):
    recipe = Recipe.objects(id=id, author=current_user._get_current_object()).first()
    if not recipe:
        return jsonify({"error": "Recipe not found or unauthorized"}), 404
    recipe.delete()
    return jsonify({"message": "Recipe deleted successfully"}), 200


# ---------------- MAIN ---------------- #

if __name__ == "__main__":
    app.run(debug=True)
