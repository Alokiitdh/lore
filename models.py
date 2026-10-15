from datetime import datetime, timezone
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


# Created without an app; main.py connects it with db.init_app(app).
db = SQLAlchemy()

# Each class is a table; each db.Column is a column. The table name is the
# class name in lowercase ('user', 'post').
# UserMixin gives User the methods flask-login expects (is_authenticated,
# is_active, is_anonymous, get_id), so we don't have to write them ourselves.
class User(db.Model, UserMixin):
    # primary_key: the database assigns each user a unique id automatically.
    id = db.Column(db.Integer, primary_key = True)
    # unique=True makes the database itself reject duplicates; forms.py
    # also checks first so the user gets a friendly message instead of a crash.
    username = db.Column(db.String(20), unique = True, nullable = False)
    email = db.Column(db.String(120), unique = True, nullable = False)
    # Just the filename of the profile picture; every user starts with the default.
    image_file = db.Column(db.String(20), nullable = False, default = 'default.jpg')
    # Stores the password *hash*, not the password. Hashes from
    # werkzeug's generate_password_hash are ~160 chars, hence 255.
    password = db.Column(db.String(255), nullable = False)
    # backref='author' adds a `post.author` attribute on every Post,
    # which is how home.html shows `post.author.username`.
    posts = db.relationship('Post', backref = 'author', lazy=True)

    # What you see when printing a User (handy in the shell/debugger).
    # The password hash is deliberately left out.
    def __repr__(self):
        return f'user({self.username}, {self.email}, {self.image_file})'

class Post(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(100), nullable = False)
    # A lambda so the time is taken when each post is created, not once at import.
    date_posted = db.Column(db.DateTime, nullable=False, default = lambda: datetime.now(timezone.utc))
    # Text (unlimited length) rather than String, since blog posts can be long.
    content = db.Column(db.Text, nullable = False )
    # Foreign key: stores the id of the user who wrote the post. 'user.id' is
    # the *table* name (lowercase), not the User class.
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable = False)

    def __repr__(self):
        return f'Post({self.title}, {self.date_posted})'
