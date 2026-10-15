import os
import secrets
from urllib.parse import urlparse
from flask import Flask, render_template, flash, redirect, url_for, request
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForms, LoginForms, UpdatePictureForm
from models import Post, User, db

app = Flask(__name__)
# SECRET_KEY signs the session cookie (which is where flask-login keeps the logged-in user)
# and the CSRF tokens in our forms. Set a real random value via the env var in production.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-only-change-me')
# A relative SQLite path; Flask-SQLAlchemy puts the file in the instance/ folder.
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
# Flask rejects bigger requests with a 413 error before our code runs (handled below).
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# `db` is created in models.py without an app, then attached here. Keeping it
# in its own module lets forms.py and models.py import it without importing
# main.py, which would cause a circular import.
db.init_app(app)




# ---------------------------------------------------------------------------
# Authentication setup (flask-login)
# ---------------------------------------------------------------------------
# LoginManager handles the session side of auth: remembering who is logged in
# between requests, and exposing them everywhere as `current_user`.
login_manager = LoginManager(app)
login_manager.login_view = 'login'               # where @login_required sends logged-out users
login_manager.login_message_category = 'info'    # Bootstrap alert class for the "please log in" flash


@login_manager.user_loader
def load_user(user_id):
    # flask-login only stores the user's id in the session cookie (never the
    # password or full object). On every request it calls this function to
    # turn that id back into a User row from the database.
    return db.session.get(User, int(user_id))


# ---------------------------------------------------------------------------
# Profile pictures
# ---------------------------------------------------------------------------
PROFILE_PICS_DIR = os.path.join(app.root_path, 'static', 'profile_pics')
DEFAULT_PICTURE = 'default.jpg'   # the value models.py stores for users without a photo


def avatar_url(user):
    # Users without an uploaded photo get the blank-circle SVG. Mapping the
    # stored 'default.jpg' here means existing rows need no database change.
    if user.image_file == DEFAULT_PICTURE:
        return url_for('static', filename='profile_pics/default.svg')
    return url_for('static', filename='profile_pics/' + user.image_file)

# Makes avatar_url() callable from every template.
app.jinja_env.globals['avatar_url'] = avatar_url


def save_picture(form_picture):
    """Crop/resize the upload to a 250x250 JPEG and return its new filename.

    Raises UnidentifiedImageError if the file isn't a real image.
    """
    image = Image.open(form_picture)
    image = ImageOps.exif_transpose(image)                  # respect phone camera rotation
    image = ImageOps.fit(image, (250, 250)).convert('RGB')  # centre-crop to a square; JPEG has no alpha
    # A random name avoids clashes between users and stops the browser
    # showing a cached old picture. 16 hex chars + '.jpg' fits String(20).
    filename = secrets.token_hex(8) + '.jpg'
    image.save(os.path.join(PROFILE_PICS_DIR, filename), quality=90)
    return filename


@app.errorhandler(413)
def file_too_large(error):
    flash('Image too large (max 5 MB).', 'danger')
    return redirect(url_for('account'))


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
POSTS_PER_PAGE = 8

@app.route('/')
@app.route('/home')
def home():
    # Only one page of posts is loaded, newest first. db.paginate adds
    # LIMIT/OFFSET to the query (plus a COUNT for the page total), so page 1
    # and page 10,000 cost the same no matter how many posts exist.
    # type=int makes ?page=abc fall back to page 1.
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(
        db.select(Post)
          # Load each post's author in the same query; otherwise post.author in
          # the template runs one extra query per post (the "N+1" problem).
          .options(db.joinedload(Post.author))
          .order_by(Post.date_posted.desc()),
        page=page, per_page=POSTS_PER_PAGE,
        error_out=False,   # don't 404 on bad page numbers; handled just below
    )
    # A page past the end (e.g. an old bookmark) goes to the last real page.
    if posts.pages and page > posts.pages:
        return redirect(url_for('home', page=posts.pages))
    return render_template('home.html', posts=posts)

@app.route('/about')
def about():
    return render_template('about.html', title = 'About')

@app.route('/register', methods=['GET', 'POST'])
def register():
    # A logged-in user has no reason to see the sign-up page.
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = RegistrationForms()
    if form.validate_on_submit():
        # Never store the plain password. generate_password_hash salts and
        # hashes it (scrypt), so even someone who reads the database can't
        # recover the original password.
        hashed_password = generate_password_hash(form.password.data)
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()

        # The account was just created with credentials the user typed a
        # moment ago, so asking them to log in again adds friction without
        # adding security. Start their session immediately instead.
        # (If we add email verification later, this is where we'd redirect
        # to a "check your inbox" page instead.)
        login_user(user)
        flash(f'Welcome, {user.username}! Your account has been created.', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', title='Register', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))

    form = LoginForms()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(email=form.email.data)
        ).scalar_one_or_none()

        # check_password_hash re-hashes the typed password with the stored salt
        # and compares it to the saved hash; we never decrypt anything.
        if user and check_password_hash(user.password, form.password.data):
            # login_user writes the user's id into the session. With
            # remember=True it also sets a long-lived cookie, so the user
            # stays logged in after closing the browser.
            login_user(user, remember=form.remember.data)

            # If @login_required bounced the user here, the original page is
            # in ?next=. Only follow it when it's a relative path on our own
            # site; otherwise a crafted link could redirect to a phishing site.
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('home')
            return redirect(next_page)

        # Same message whether the email or the password was wrong, so the
        # login page doesn't reveal which emails have accounts.
        flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)

@app.route('/logout')
def logout():
    # Clears the user from the session (and the remember-me cookie).
    logout_user()
    return redirect(url_for('home'))

@app.route('/account', methods=['GET', 'POST'])
@login_required   # logged-out visitors are redirected to login_view ('login') with ?next=/account
def account():
    form = UpdatePictureForm()
    if form.validate_on_submit():
        try:
            new_file = save_picture(form.picture.data)
        except UnidentifiedImageError:
            flash('That file is not a valid image.', 'danger')
            return redirect(url_for('account'))

        old_file = current_user.image_file
        current_user.image_file = new_file
        db.session.commit()

        # Remove the replaced upload so old pictures don't pile up (never the default).
        if old_file != DEFAULT_PICTURE:
            old_path = os.path.join(PROFILE_PICS_DIR, old_file)
            if os.path.exists(old_path):
                os.remove(old_path)

        flash('Your profile picture has been updated.', 'success')
        # Redirect after POST so refreshing the page doesn't re-upload.
        return redirect(url_for('account'))
    return render_template('account.html', title='Account', form=form)


# Runs only for `python main.py`, not when another module imports main
# (e.g. `flask run` or a test script).
if __name__ == '__main__':
    with app.app_context():
        # Creates any tables that don't exist yet. It does NOT alter existing
        # tables, so after changing a model, delete instance/site.db (or use migrations).
        db.create_all()
    app.run(debug=True)
