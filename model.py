import datetime
from flask_bcrypt import generate_password_hash, check_password_hash
from flask_login import UserMixin
from mongoengine import *
import os

MONGO_URI = os.getenv("MONGO_URI")


connect(
    host=MONGO_URI,
)

# ---------------- User Model ----------------
class User(UserMixin, Document):
    username = StringField(required=True, unique=True, max_length=50)
    email = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    profile_picture = StringField()  # store URL or path of profile picture
    created_at = DateTimeField(default=datetime.datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __str__(self):
        return self.username


# ---------------- Comment Embedded Document ----------------
class Comment(EmbeddedDocument):
    user = ReferenceField(User, required=True)
    content = StringField(required=True)
    created_at = DateTimeField(default=datetime.datetime.utcnow)


# ---------------- Recipe Model ----------------
class Recipe(Document):
    title = StringField(required=True, max_length=100)
    description = StringField()
    ingredients = ListField(StringField())
    steps = ListField(StringField())
    image_url = StringField()
    cuisine = StringField(choices=["Indian", "Italian", "Chinese", "Mexican", "Other"])
    difficulty = StringField(choices=["Easy", "Medium", "Hard"])
    cooking_time = IntField(help_text="time in minutes")
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    # Relationships
    author = ReferenceField(User, reverse_delete_rule=CASCADE)
    likes = ListField(ReferenceField(User))  # Users who liked this recipe
    comments = ListField(EmbeddedDocumentField(Comment))  # Embedded comments

    meta = {
        'indexes': ['title', 'cuisine', 'difficulty'],
        'ordering': ['-created_at']
    }

    def __str__(self):
        return f"{self.title} by {self.author.username}"
    
    def like_recipe(self, user):
        """Add a like from a user if not already liked."""
        if user not in self.likes:
            self.likes.append(user)
            self.save()

    def unlike_recipe(self, user):
        """Remove a like from a user."""
        if user in self.likes:
            self.likes.remove(user)
            self.save()

    def add_comment(self, user, content):
        """Add a comment to the recipe."""
        comment = Comment(user=user, content=content)
        self.comments.append(comment)
        self.save()
