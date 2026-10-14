from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Length, Email, EqualTo

class RegistrationForms(FlaskForm):
    username = StringField(label='Username', 
                           validators=[ DataRequired(), Length(max=20, min=4)] )
    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', 
                             validators=[DataRequired()])
    confirm_password = PasswordField(label='Confirm Password', 
                                     validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField(label='Sign Up ')

class LoginForms(FlaskForm):

    email = StringField(label='Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField(label='Password', 
                             validators=[DataRequired()])
    remember = BooleanField(label='Remember me')

    submit = SubmitField(label='Login ')

    
    