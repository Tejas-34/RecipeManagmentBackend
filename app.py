from flask import Flask, request, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from model import User, Recipe
import datetime
from flask_cors import CORS, cross_origin
import os
import jwt
from functools import wraps


app = Flask(__name__)
app.secret_key = "sudsfasdfasdfhyknfkwfkwfjsadf"


CORS(app)


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Headers'] = request.headers.get('Access-Control-Request-Headers', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        
        return response, 200

# app.py

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method == "OPTIONS":
            return f(*args, **kwargs)
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split()[1]
            except IndexError:
                return jsonify({'error': 'Token is missing or malformed'}), 401
        
        if not token:
            # NOTE: If the OPTIONS bypass failed, this is the 401 the browser 
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Decode the token and load the current_user
            data = jwt.decode(token, app.secret_key, algorithms=["HS256"])
            current_user = User.objects(pk=data['user_id']).first()
            if not current_user:
                 return jsonify({'error': 'User not found'}), 401
                 
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token is expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Token is invalid'}), 401
            
        return f(current_user, *args, **kwargs)
    return decorated



UPLOAD_FOLDER = os.path.join(os.getcwd(), "static/uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)




@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)



# ---------------- AUTH ROUTES ---------------- #

@app.route("/register", methods=["POST"])
def register():
    data = request.form
    if User.objects(username=data["username"]).first():
        return jsonify({"error": "Username already exists"}), 400
    if User.objects(email=data["email"]).first():
        return jsonify({"error": "Email already exists"}), 400

    user = User(username=data["username"], email=data["email"])
    user.set_password(data["password"])

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
        token_payload = {
            'user_id': str(user.id),
            'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
            'iat': datetime.datetime.utcnow()
        }
        token = jwt.encode(token_payload, app.secret_key, algorithm="HS256")
        
        return jsonify({
            "message": "Logged in successfully",
            "token": token,
            "user": {
                "username": user.username,
                "email": user.email,
                "profile_picture": user.profile_picture or None
            }
        })
    
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout", methods=["GET"])
@token_required
def logout(current_user):
    return jsonify({"message": "Logged out successfully (token discarded)"})


# ---------------- RECIPE ROUTES ---------------- #

@app.route("/recipes", methods=["POST"])
@token_required
def create_recipe(current_user):
    data = request.form
    recipe = Recipe(
        title=data["title"],
        description=data.get("description"),
        ingredients=data.getlist("ingredients"),
        steps=data.getlist("steps"),
        cuisine=data.get("cuisine"),
        difficulty=data.get("difficulty"),
        cooking_time=int(data.get("cooking_time", 0)),
        author=current_user
    )

    if "image" in request.files:
        file = request.files["image"]
        filename = f"{current_user.username}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        recipe.image_url = f"static/uploads/{filename}"
        
        file.save(filepath)

    recipe.save()
    return jsonify({"message": "Recipe created successfully", "recipe_id": str(recipe.id)})

@app.route("/recipes/<recipe_id>/like", methods=["POST"])
@token_required
def like_recipe(current_user, recipe_id):
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
@token_required
def comment_recipe(current_user, recipe_id):
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
        comment_list = []
        for c in r.comments:
            comment_list.append({
                "user": {"username": c.user.username}, 
                "content": c.content
            })
            
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
            "comments": comment_list 
        })
    return jsonify(result)


@app.route("/recipes/my", methods=["GET"])
@token_required
def list_my_recipes(current_user):
    """Fetches all recipes created by the currently authenticated user."""

    recipes = Recipe.objects(author=current_user.id)
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



@app.route("/recipes/<recipe_id>", methods=["PUT"])
@token_required
def update_recipe(current_user, recipe_id):
    """Allows the author to update a specific recipe."""
    recipe = Recipe.objects(pk=recipe_id).first()
    
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404
        
    # Check if the current user is the author
    if recipe.author.id != current_user.id:
        return jsonify({"error": "Unauthorized to edit this recipe"}), 403

    data = request.form
    update_fields = {}

    # Gather fields from form data
    if "title" in data: update_fields['title'] = data["title"]
    if "description" in data: update_fields['description'] = data["description"]
    if data.get("ingredients"): update_fields['ingredients'] = data.getlist("ingredients")
    if data.get("steps"): update_fields['steps'] = data.getlist("steps")
    if "cuisine" in data: update_fields['cuisine'] = data["cuisine"]
    if "difficulty" in data: update_fields['difficulty'] = data["difficulty"]
    if "cooking_time" in data: 
        try:
            update_fields['cooking_time'] = int(data["cooking_time"])
        except ValueError:
            pass
            
    # Handle image replacement
    if "image" in request.files:
        file = request.files["image"]
        filename = f"{current_user.username}_{file.filename}"
        filepath = os.path.join(UPLOAD_FOLDER, filename)
        file.save(filepath)
        update_fields['image_url'] = f"/uploads/{filename}"

    # Perform the update
    if update_fields:
        recipe.update(**update_fields)
        return jsonify({"message": "Recipe updated successfully", "recipe_id": str(recipe.id)})
    
    return jsonify({"message": "No fields to update"}), 200


@app.route("/recipes/<recipe_id>", methods=["DELETE"])
@token_required
def delete_recipe(current_user, recipe_id):
    """Allows the author to delete a specific recipe."""
    recipe = Recipe.objects(pk=recipe_id).first()
    
    if not recipe:
        return jsonify({"error": "Recipe not found"}), 404
        
    # Check if the current user is the author
    if recipe.author.id != current_user.id:
        return jsonify({"error": "Unauthorized to delete this recipe"}), 403

    # Delete the recipe
    recipe.delete()
    return jsonify({"message": "Recipe deleted successfully"}), 200


@app.errorhandler(500)
def internal_error(e):
    return jsonify({"error": "Internal Server Error"}), 500


@app.route("/test", methods=["GET"])
@token_required
def test(current_user):
    return jsonify({"message": "Welcome to the Recipe API"})

if __name__ == "__main__":
    app.run(debug=True)
