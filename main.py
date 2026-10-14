from flask import Flask, render_template, flash, redirect, url_for
from forms import RegistrationForms, LoginForms

app = Flask(__name__)

app.config['SECRET_KEY'] = '0f428d55e0c79cc18c890094c231f316'

posts = [
    {
        'author': 'Alok',
        'title': 'Blog Post 1',
        'content': 'First post content',
        'date_posted': 'April 20, 2026'
    },
    {
        'author': 'Jane Doe',
        'title': 'Blog Post 2',
        'content': 'First post content',
        'date_posted': 'April 20, 2027'
    }
]


@app.route('/')
@app.route('/home')
def home():
    return render_template('home.html', posts= posts)

@app.route('/about')
def about():
    return render_template('about.html', title = 'About')

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForms()
    if form.validate_on_submit():
        flash(f'Account succesfullyy created for {form.username.data}!!', 'success')
        return redirect(url_for('home'))
    return render_template('register.html', form= form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForms()
    if form.validate_on_submit():
        if form.email.data == 'admin@blog.com' and form.password.data == 'password':
            flash('You have been logged in!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check username and password', 'danger')
    return render_template('login.html', form = form)


## If we want to run our script with the python way , then we willa dd this 
if __name__ == '__main__':
    app.run(debug=True)
 