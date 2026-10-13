from flask import Flask, render_template

app = Flask(__name__)


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
def home():
    return render_template('home.html', posts= posts)

@app.route('/about')
def about():
    return render_template('about.html', title = 'About')


## If we want to run our script with the python way , then we willa dd this 
if __name__ == '__main__':
    app.run(debug=True)
 