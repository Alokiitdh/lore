from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from flask_login import current_user
from models import User, db

# FlaskForm (from Flask-WTF) adds CSRF protection on top of plain WTForms:
# each form carries a hidden token signed with SECRET_KEY, rendered in the
# templates by form.hidden_tag(). validate_on_submit() in main.py runs every
# validator below and only returns True for a valid POST.

class RegistrationForms(FlaskForm):
    username = StringField(label='Username',
                           validators=[ DataRequired(), Length(max=20, min=4)] )   # max matches String(20) in models.py
    # Email() checks the format; it needs the email-validator package.
    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    # PasswordField renders <input type="password"> so the typing is hidden.
    password = PasswordField(label='Password',
                             validators=[DataRequired(), Length(min=6)])
    # EqualTo('password') fails unless both password boxes match.
    confirm_password = PasswordField(label='Confirm Password',
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(label='Sign Up ')

    # WTForms automatically runs any method named validate_<fieldname> as an
    # extra validator for that field. Checking for duplicates here means the
    # user sees a friendly error under the field, instead of the app crashing
    # with an IntegrityError when the UNIQUE constraint fails on insert.
    def validate_username(self, username):
        user = db.session.execute(db.select(User).filter_by(username=username.data)).scalar_one_or_none()
        if user:
            raise ValidationError('The Username is already taken')

    def validate_email(self, email):
        user = db.session.execute(db.select(User).filter_by(email=email.data)).scalar_one_or_none()
        if user:
            raise ValidationError('The Email is already registered')

class LoginForms(FlaskForm):
    # Only checks that the fields are filled in and well-formed. Whether the
    # email/password are actually correct is checked in the login() route,
    # so a wrong login doesn't reveal which part was wrong.
    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField(label='Password',
                             validators=[DataRequired()])
    # Passed to login_user(remember=...) to keep the user logged in across browser restarts.
    remember = BooleanField(label='Remember me')

    submit = SubmitField(label='Login ')

class UpdatePictureForm(FlaskForm):
    # FileAllowed only checks the file extension. save_picture() in main.py
    # opens the file with Pillow, which also rejects files that aren't real images.
    picture = FileField(label='Profile picture',
                        validators=[FileRequired(), FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Images only (jpg, png, webp)')])
    submit = SubmitField(label='Upload')

class UpdateAccountForm(FlaskForm):
    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    # Optional(): leave both password boxes empty to keep the current password.
    new_password = PasswordField(label='New Password',
                                 validators=[Optional(), Length(min=6)])
    confirm_password = PasswordField(label='Confirm New Password',
                                     validators=[EqualTo('new_password', message='Passwords must match')])
    # Required for any change, so someone at an unlocked, logged-in computer
    # can't take over the account. Checked against the hash in the route.
    current_password = PasswordField(label='Current Password',
                                     validators=[DataRequired()])
    # Named `update` (not `submit`) so account() can tell this form apart
    # from the picture form on the same page.
    update = SubmitField(label='Save Changes')

    def validate_email(self, email):
        if email.data == current_user.email:
            return
        user = db.session.execute(db.select(User).filter_by(email=email.data)).scalar_one_or_none()
        if user:
            raise ValidationError('The Email is already registered')

class RequestResetForm(FlaskForm):
    # No "does this email exist?" check here, on purpose: the route shows the
    # same message either way so the form can't be used to discover accounts.
    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    submit = SubmitField(label='Send Reset Link')

class PostForm(FlaskForm):
    # Used for both creating and updating a post.
    title = StringField(label='Title',
                        validators=[DataRequired(), Length(max=100)])   # max matches String(100) in models.py
    content = TextAreaField(label='Content',
                            validators=[DataRequired()])
    submit = SubmitField(label='Post')

class DeletePostForm(FlaskForm):
    # No fields: it exists so the delete button sends a CSRF token, which stops
    # other sites from tricking a logged-in user into deleting their posts.
    submit = SubmitField(label='Delete')

class ResetPasswordForm(FlaskForm):
    password = PasswordField(label='New Password',
                             validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(label='Confirm New Password',
                                     validators=[DataRequired(), EqualTo('password', message='Passwords must match')])
    submit = SubmitField(label='Reset Password')
