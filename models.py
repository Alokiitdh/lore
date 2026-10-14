from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()


# UserMixin gives User the methods flask-login expects (is_authenticated,
# is_active, is_anonymous, get_id), so we don't have to write them ourselves.
class User(db.Model, UserMixin):
    # id Column, user column, Email column, profile image column
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(20), unique = True, nullable = False)
    email = db.Column(db.String(120), unique = True, nullable = False)
    image_file = db.Column(db.String(20), nullable = False, default = 'default.jpg')
    # Stores the password *hash*, not the password. Hashes from
    # werkzeug's generate_password_hash are ~160 chars, hence 255.
    password = db.Column(db.String(255), nullable = False)
    # backref='author' adds a `post.author` attribute on every Post,
    # which is how home.html shows `post.author.username`.
    posts = db.relationship('Post', backref = 'author', lazy=True)

    def __repr__(self):
        return f'user({self.username}, {self.email}, {self.image_file})'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(100), nullable = False)
    # A lambda so the time is taken when each post is created, not once at import.
    date_posted = db.Column(db.DateTime, nullable=False, default = lambda: datetime.now(timezone.utc))
    content = db.Column(db.Text, nullable = False )
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)

    def __repr__(self):
        return f'Post({self.title}, {self.date_posted})'
