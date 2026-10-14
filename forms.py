from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models import User, db

class RegistrationForms(FlaskForm):
    username = StringField(label='Username',
                           validators=[ DataRequired(), Length(max=20, min=4)] )
    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField(label='Password',
                             validators=[DataRequired(), Length(min=6)])
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

    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField(label='Password',
                             validators=[DataRequired()])
    # Passed to login_user(remember=...) to keep the user logged in across browser restarts.
    remember = BooleanField(label='Remember me')

    submit = SubmitField(label='Login ')
