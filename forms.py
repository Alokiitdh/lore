from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
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
