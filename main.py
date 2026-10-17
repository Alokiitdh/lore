import os
import secrets
import smtplib
from email.message import EmailMessage
from urllib.parse import urlparse
from dotenv import load_dotenv
from flask import Flask, render_template, flash, redirect, url_for, request, abort
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from markupsafe import Markup
from PIL import Image, ImageOps, UnidentifiedImageError
from werkzeug.security import generate_password_hash, check_password_hash
from forms import (RegistrationForms, LoginForms, UpdatePictureForm, UpdateAccountForm, PostForm, DeletePostForm,
                   RequestResetForm, ResetPasswordForm)
from models import Post, User, db

# Reads KEY=value lines from the .env file next to this script into
# os.environ (SECRET_KEY, MAIL_* ...). .env is git-ignored because it holds
# secrets; .env.example shows which keys it should have.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

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
# Custom error pages
# ---------------------------------------------------------------------------
# Flask calls these instead of showing its plain default error pages. The
# second value in each return keeps the real status code; without it the
# browser would get "200 OK" for an error page.
def error_page(code, heading, message):
    return render_template('errors/error.html', title=heading,
                           code=code, heading=heading, message=message), code


@app.errorhandler(403)
def forbidden(error):
    # e.g. trying to update or delete someone else's post
    return error_page(403, "You don't have permission to do that",
                      'You can only change or delete your own posts.')


@app.errorhandler(404)
def page_not_found(error):
    # unknown URLs, and posts or users that don't exist
    return error_page(404, 'Page not found',
                      "That page doesn't exist. It may have been deleted, or the link may be wrong.")


@app.errorhandler(500)
def internal_error(error):
    # Any unhandled exception. A failed database write leaves the session in
    # a broken state, so undo it before rendering (layout.html uses current_user).
    db.session.rollback()
    return error_page(500, 'Something went wrong',
                      "That's a problem on our side, not yours. Please try again in a moment.")


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

@app.route('/user/<string:username>')
def user_posts(username):
    # Same as home(), but only one user's posts. An unknown username gives a 404.
    user = db.first_or_404(db.select(User).filter_by(username=username))
    page = request.args.get('page', 1, type=int)
    posts = db.paginate(
        db.select(Post)
          .filter_by(user_id=user.id)
          .options(db.joinedload(Post.author))
          .order_by(Post.date_posted.desc()),
        page=page, per_page=POSTS_PER_PAGE, error_out=False,
    )
    if posts.pages and page > posts.pages:
        return redirect(url_for('user_posts', username=username, page=posts.pages))
    return render_template('user_posts.html', posts=posts, user=user, title=user.username)


# ---------------------------------------------------------------------------
# Single posts: view, create, update, delete
# ---------------------------------------------------------------------------
def get_own_post_or_403(post_id):
    # Only the author may change or delete a post. Anyone else gets
    # 403 Forbidden, even if they type the URL in by hand.
    post = db.get_or_404(Post, post_id)
    if post.author != current_user:
        abort(403)
    return post


@app.route('/post/new', methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created.', 'success')
        return redirect(url_for('post', post_id=post.id))
    return render_template('create_post.html', title='New Post', form=form, legend='New Post')


@app.route('/post/<int:post_id>')
def post(post_id):
    post = db.get_or_404(Post, post_id)
    return render_template('post.html', title=post.title, post=post, delete_form=DeletePostForm())


@app.route('/post/<int:post_id>/update', methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = get_own_post_or_403(post_id)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated.', 'success')
        return redirect(url_for('post', post_id=post.id))
    if request.method == 'GET':
        # Pre-fill the form with the current text.
        form.title.data = post.title
        form.content.data = post.content
    form.submit.label.text = 'Update'
    return render_template('create_post.html', title='Update Post', form=form, legend='Update Post')


# POST only: deleting must never happen just by visiting a link.
@app.route('/post/<int:post_id>/delete', methods=['POST'])
@login_required
def delete_post(post_id):
    post = get_own_post_or_403(post_id)
    if not DeletePostForm().validate_on_submit():   # missing/invalid CSRF token
        abort(400)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted.', 'success')
    return redirect(url_for('home'))

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
    # prefix='account' gives this form's fields distinct names/ids (account-email, ...)
    # so the two forms on the page don't clash.
    account_form = UpdateAccountForm(prefix='account')

    # Both forms post to /account. Only the settings form sends its `update`
    # button; the picture form is submitted by JS without a button.
    if account_form.update.data:
        if account_form.validate_on_submit():
            if not check_password_hash(current_user.password, account_form.current_password.data):
                account_form.current_password.errors.append('Current password is incorrect')
            else:
                current_user.email = account_form.email.data
                if account_form.new_password.data:
                    current_user.password = generate_password_hash(account_form.new_password.data)
                db.session.commit()
                flash('Your account has been updated.', 'success')
                return redirect(url_for('account'))
    elif form.validate_on_submit():
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

    # Pre-fill the email box unless we're re-showing what the user just typed.
    if not account_form.update.data:
        account_form.email.data = current_user.email
    return render_template('account.html', title='Account', form=form, account_form=account_form)


# ---------------------------------------------------------------------------
# Password reset ("Forgot password?")
# ---------------------------------------------------------------------------
RESET_TOKEN_MAX_AGE = 30 * 60   # seconds a reset link stays valid


def _reset_serializer():
    # Signs tokens with SECRET_KEY, so they can't be forged or edited. The salt
    # keeps these tokens from being valid for any other signed-data purpose.
    return URLSafeTimedSerializer(app.config['SECRET_KEY'], salt='password-reset')


def get_reset_token(user):
    # Including the end of the current password hash makes the link single-use:
    # once the password changes, the hash changes and old links stop matching.
    return _reset_serializer().dumps({'id': user.id, 'pw': user.password[-12:]})


def verify_reset_token(token):
    """Return the User for a valid token, or None if it's expired, tampered or already used."""
    try:
        data = _reset_serializer().loads(token, max_age=RESET_TOKEN_MAX_AGE)
    except (SignatureExpired, BadSignature):
        return None
    user = db.session.get(User, data.get('id'))
    if user is None or user.password[-12:] != data.get('pw'):
        return None
    return user


def mail_configured():
    # All three are needed to send. A half-filled .env (e.g. a blank
    # MAIL_PASSWORD) counts as "not configured" and uses dev mode instead.
    return all(os.environ.get(key) for key in ('MAIL_SERVER', 'MAIL_USERNAME', 'MAIL_PASSWORD'))


def send_reset_email(user, link):
    """Email the reset link. Returns True if it was sent, False if sending failed."""
    msg = EmailMessage()
    msg['Subject'] = 'Reset your Lore password'
    msg['From'] = os.environ.get('MAIL_SENDER') or os.environ['MAIL_USERNAME']
    msg['To'] = user.email
    msg.set_content(f'Hi {user.username},\n\n'
                    f'To reset your Lore password, open this link (valid for 30 minutes):\n{link}\n\n'
                    "If you didn't ask for this, just ignore this email; your password won't change.\n")
    try:
        with smtplib.SMTP(os.environ['MAIL_SERVER'], int(os.environ.get('MAIL_PORT') or 587), timeout=15) as smtp:
            smtp.starttls()
            smtp.login(os.environ['MAIL_USERNAME'], os.environ['MAIL_PASSWORD'])
            smtp.send_message(msg)
    except (smtplib.SMTPException, OSError):
        # Wrong app password, no internet, etc. The full error goes to the
        # terminal; the user just sees a friendly message.
        app.logger.exception('Could not send password reset email to %s', user.email)
        return False
    return True


@app.route('/reset_password', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = db.session.execute(
            db.select(User).filter_by(email=form.email.data)
        ).scalar_one_or_none()
        if user:
            link = url_for('reset_token', token=get_reset_token(user), _external=True)
            if not mail_configured():
                # Dev mode (no mail settings in .env): show the link on the page
                # and in the terminal instead of emailing it. Never happens once
                # mail is configured, so a real site never puts links on screen.
                app.logger.warning('DEV MODE, email not configured. Reset link for %s:\n%s', user.email, link)
                flash(Markup('Email is not set up yet (dev mode). '
                             '<a href="{}">Click here to reset your password</a>.').format(link), 'warning')
                return redirect(url_for('login'))
            if not send_reset_email(user, link):
                flash("We couldn't send the email right now. Please try again later.", 'danger')
                return redirect(url_for('reset_request'))
        # Same message whether or not the account exists, so this page
        # can't be used to find out who has an account.
        flash('If an account exists for that email, a reset link has been sent.', 'info')
        return redirect(url_for('login'))
    return render_template('reset_request.html', title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user = verify_reset_token(token)
    if user is None:
        flash('That reset link is invalid or has expired. Please request a new one.', 'warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = generate_password_hash(form.password.data)
        db.session.commit()
        flash('Your password has been reset. You can now log in.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_token.html', title='Reset Password', form=form)


# Runs only for `python main.py`, not when another module imports main
# (e.g. `flask run` or a test script).
if __name__ == '__main__':
    with app.app_context():
        # Creates any tables that don't exist yet. It does NOT alter existing
        # tables, so after changing a model, delete instance/site.db (or use migrations).
        db.create_all()
    app.run(debug=True)
