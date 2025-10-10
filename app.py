from flask import Flask, request, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from model import User, Recipe
import datetime
from flask_cors import CORS
import os
import jwt
from functools import wraps


app = Flask(__name__)
app.secret_key = "sudsfasdfasdfhyknfkwfkwfjsadf"


app.config['SESSION_COOKIE_SAMESITE'] = None
app.config['SESSION_COOKIE_SECURE'] = False 

CORS(app, supports_credentials=True)

login_manager = LoginManager()
login_manager.init_app(app)

UPLOAD_FOLDER = os.path.join(os.getcwd(), "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@login_manager.user_loader
def load_user(user_id):
    return User.objects(pk=user_id).first()


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)



# ---------------- AUTH ROUTES ---------------- #

@app.route("/register", methods=["POST"])
def register():
    data = request.form  # We'll use form-data to support file uploads
    if User.objects(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 400
    if User.objects(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    user = User(username=data["username"], email=data["email"])

    # Password
    user.set_password(data["password"])

    # Profile Picture
    if "profile_picture" in request.files:
        file = request.files["profile_picture"]
        filename = f"{user.username}_{file.filename}"
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        user.profile_picture = f"/static/uploads/{filename}"

    user.save()
    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.objects(username=data["username"]).first()
    if user and user.check_password(data["password"]):
        login_user(user)
        # print(data["username"], data["password"])
        return jsonify({
            "message": "Logged in successfully",
            "user": {
                "username": user.username,
                "email": user.email,
                "profile_picture": user.profile_picture or None
            }
        })
    
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout", methods=["GET"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logged out successfully"})


# ---------------- RECIPE ROUTES ---------------- #

@app.route("/recipes", methods=["POST"])
@login_required
def create_recipe():
    data = request.form
    recipe = Recipe(
        title=data["title"],
        description=data.get("description"),
        ingredients=data.getlist("ingredients"),  # ingredients[]=sugar&ingredients[]=milk
        steps=data.getlist("steps"),
        cuisine=data.get("cuisine"),
        difficulty=data.get("difficulty"),
        cooking_time=int(data.get("cooking_time", 0)),
        author=current_user
    )

    # Recipe image
    if "image" in request.files:
        file = request.files["image"]
        filename = f"{current_user.username}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        recipe.image_url = filepath

    recipe.save()
    return jsonify({"message": "Recipe created successfully", "recipe_id": str(recipe.id)})


@app.route("/recipes/<recipe_id>/like", methods=["POST"])
@login_required
def like_recipe(recipe_id):
    recipe = Recipe.objects(pk=recipe_id).first()
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404
    if current_user in recipe.likes:
        recipe.unlike_recipe(current_user)
        return jsonify({"message": "Unliked recipe"})
    else:
        recipe.like_recipe(current_user)
        return jsonify({"message": "Liked recipe"})


@app.route("/recipes/<recipe_id>/comment", methods=["POST"])
@login_required
def comment_recipe(recipe_id):
    data = request.json
    recipe = Recipe.objects(pk=recipe_id).first()
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404
    content = data.get("content")
    if not content:
        return jsonify({"error": "Comment content required"}), 400
    recipe.add_comment(current_user, content)
    return jsonify({"message": "Comment added successfully"})


@app.route("/recipes", methods=["GET"])
def list_recipes():
    recipes = Recipe.objects()
    result = []
    for r in recipes:
        result.append({
            "id": str(r.id),
            "title": r.title,
            "description": r.description,
            "ingredients": r.ingredients,
            "steps": r.steps,
            "image_url": r.image_url,
            "cuisine": r.cuisine,
            "difficulty": r.difficulty,
            "cooking_time": r.cooking_time,
            "author": r.author.username,
            "likes_count": len(r.likes),
            "comments": [{"user": c.user.username, "content": c.content} for c in r.comments]
        })
    return jsonify(result)


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal Server Error"}), 500


# test route
@app.route("/test", methods=["GET"])
@login_required
def test():
    return jsonify({"message": "Welcome to the Recipe API"})

if __name__ == "__main__":
    app.run(debug=True)