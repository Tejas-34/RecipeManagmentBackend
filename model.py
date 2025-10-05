import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import UserMixin
from mongoengine import *
# from app import db

connect(
    db="Recipe",
    host="mongodb+srv://22f1001500_db_user:1N4f7lU9WbXOHklo@recipe.zmbe8zj.mongodb.net/?retryWrites=true&w=majority&appName=Recipe"
)

# User Model
class User(UserMixin, Document):
    username = StringField(required=True, unique=True, max_length=50)
    email = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __str__(self):
        return self.username


# Recipe Model
class Recipe(Document):
    title = StringField(required=True, max_length=100)
    description = StringField()
    ingredients = ListField(StringField())  # ["sugar", "milk", "flour"]
    steps = ListField(StringField())  # ["mix ingredients", "bake at 180C"]
    image_url = StringField()  # store uploaded image path or cloud URL
    cuisine = StringField(choices=["Indian", "Italian", "Chinese", "Mexican", "Other"])
    difficulty = StringField(choices=["Easy", "Medium", "Hard"])
    cooking_time = IntField(help_text="time in minutes")
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)
    
    # Relationships
    author = ReferenceField(User, reverse_delete_rule=CASCADE)

    meta = {
        'indexes': ['title', 'cuisine', 'difficulty'],
        'ordering': ['-created_at']
    }

    def __str__(self):
        return f"{self.title} by {self.author.username}"
