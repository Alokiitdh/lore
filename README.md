# Lore

A small, full-featured blog built with Flask. Users can sign up, write posts, upload a profile picture, browse everyone's posts page by page, and reset a forgotten password by email.

The code is written to be read: most files have comments explaining *why* things are done the way they are. That makes it useful as a reference for learning how a Flask app fits together end to end.

## Features

- **Accounts**
  - Register and log in, with "Remember me".
  - Change your email or password from the Account page; your current password is required.
- **Password reset**
  - "Forgot Password?" emails a signed reset link.
  - The link expires after 30 minutes and works only once.
- **Profile pictures**
  - Everyone starts with a blank avatar.
  - Click the avatar on the Account page to upload a JPG, PNG or WebP (up to 5 MB). It's cropped to a 250×250 square automatically.
- **Posts**
  - Create, read, update and delete posts.
  - Only the author sees the Update and Delete buttons, and the server enforces this too.
  - Deleting asks for confirmation first.
- **Feeds with pagination**
  - The home page shows everyone's posts, newest first, 8 per page.
  - Each user has a page (`/user/<username>`) with only their posts, paginated the same way.
- **Custom error pages** for 403 (not your post), 404 (not found) and 500 (server error).

## Tech stack

| Area | Used |
|---|---|
| Language | Python 3.13 |
| Web framework | [Flask](https://flask.palletsprojects.com/) 3 |
| Database | SQLite via [Flask-SQLAlchemy](https://flask-sqlalchemy.readthedocs.io/) |
| Auth / sessions | [Flask-Login](https://flask-login.readthedocs.io/), Werkzeug password hashing |
| Forms + CSRF | [Flask-WTF](https://flask-wtf.readthedocs.io/) / WTForms, email-validator |
| Images | [Pillow](https://pillow.readthedocs.io/) |
| Config | [python-dotenv](https://pypi.org/project/python-dotenv/) (`.env` file) |
| Front end | Jinja2 templates, Bootstrap 4 (CDN) |
| Package manager | [uv](https://docs.astral.sh/uv/) |

## Getting started

### Prerequisites
- [uv](https://docs.astral.sh/uv/getting-started/installation/). It installs the right Python version (3.13) for you.

### 1. Clone and install
```bash
git clone https://github.com/Alokiitdh/lore.git
cd lore
uv sync
```
`uv sync` creates a `.venv` folder with every dependency from `uv.lock`.

### 2. Configure
Copy the example settings file and edit it:
```bash
cp .env.example .env
```
- Set `SECRET_KEY` to a long random string. You can generate one with:
  ```bash
  uv run python -c "import secrets; print(secrets.token_hex(32))"
  ```
- The mail settings are optional; see [Email setup](#email-setup-password-reset). The app works without them.

### 3. Run
```bash
uv run python main.py
```
Open http://127.0.0.1:5000.

The first run creates the SQLite database at `instance/site.db`.

Always start the app through `uv run` (or an activated `.venv`). Plain `python main.py` uses your system Python, which doesn't have the dependencies. That's what causes `ModuleNotFoundError: No module named 'flask'` or `'PIL'`.

## Configuration

All settings are read from environment variables, loaded automatically from `.env` at startup. `.env` is git-ignored, so secrets never get committed; `.env.example` lists the keys.

| Variable | Required | Purpose |
|---|---|---|
| `SECRET_KEY` | Yes (in production) | Signs login sessions, CSRF tokens and password-reset links. Changing it logs everyone out. |
| `MAIL_SERVER` | For email | SMTP server, e.g. `smtp.gmail.com` |
| `MAIL_PORT` | For email | SMTP port, usually `587` (STARTTLS) |
| `MAIL_USERNAME` | For email | The account that sends the emails |
| `MAIL_PASSWORD` | For email | That account's password. For Gmail, an **App Password**. |
| `MAIL_SENDER` | Optional | The "From" line, e.g. `Lore <you@gmail.com>`. Defaults to `MAIL_USERNAME`. |

## Email setup (password reset)

**Without mail settings (dev mode).** If any of `MAIL_SERVER`, `MAIL_USERNAME` or `MAIL_PASSWORD` is empty, no email is sent. Instead, the reset link appears on the login page as a clickable message and is printed in the terminal. That's enough for local testing.

**With Gmail:**
1. Turn on 2-Step Verification for the Google account.
2. Create an App Password at https://myaccount.google.com/apppasswords.
3. Fill in `.env`:
   ```
   MAIL_SERVER=smtp.gmail.com
   MAIL_PORT=587
   MAIL_USERNAME=you@gmail.com
   MAIL_PASSWORD=your16charapppassword
   MAIL_SENDER=Lore <you@gmail.com>
   ```
4. Restart the app.

**Check the Gmail login without sending anything:**
```bash
uv run python -c "import os,smtplib; from dotenv import load_dotenv; load_dotenv('.env'); s=smtplib.SMTP(os.environ['MAIL_SERVER'],int(os.environ['MAIL_PORT']),timeout=15); s.starttls(); s.login(os.environ['MAIL_USERNAME'],os.environ['MAIL_PASSWORD']); s.quit(); print('Gmail login OK')"
```

**If sending fails,** the user sees a friendly message and the full error is logged in the terminal:

| Error in the terminal | Usual cause |
|---|---|
| `SMTPAuthenticationError` / `535` | Wrong App Password, or `MAIL_USERNAME` isn't the account it was created on |
| Timeout | The network blocks port 587 (common on campus or office Wi-Fi) |

## Project structure

```
lore/
├── main.py              # App setup, config, helpers and all routes
├── models.py            # Database models: User, Post
├── forms.py             # WTForms forms (register, login, account, posts, reset)
├── templates/
│   ├── layout.html      # Base page: navbar, flash messages, sidebar
│   ├── _posts.html      # Macros: post list + pagination bar (shared by feeds)
│   ├── _form.html       # Macro: one form field with error display
│   ├── home.html        # Home feed
│   ├── user_posts.html  # One user's posts
│   ├── post.html        # Single post + Update/Delete (author only)
│   ├── create_post.html # New / update post form
│   ├── account.html     # Profile picture + account settings
│   ├── login.html, register.html, about.html
│   ├── reset_request.html, reset_token.html
│   └── errors/error.html  # Shared 403 / 404 / 500 page
├── static/
│   ├── main.css
│   └── profile_pics/    # Uploaded avatars + default.svg
├── instance/site.db     # SQLite database (created on first run, git-ignored)
├── .env.example         # Template for .env
├── pyproject.toml       # Project metadata and dependencies
└── uv.lock              # Exact, locked dependency versions
```

## Routes

| URL | Method | Login needed | What it does |
|---|---|---|---|
| `/`, `/home` | GET | No | All posts, newest first, paginated (`?page=N`) |
| `/user/<username>` | GET | No | One user's posts, paginated |
| `/post/<id>` | GET | No | A single post |
| `/post/new` | GET, POST | Yes | Write a new post |
| `/post/<id>/update` | GET, POST | Yes (author) | Edit a post |
| `/post/<id>/delete` | POST | Yes (author) | Delete a post |
| `/register` | GET, POST | No | Create an account |
| `/login` | GET, POST | No | Log in |
| `/logout` | GET | No | Log out |
| `/account` | GET, POST | Yes | Profile picture, email and password |
| `/reset_password` | GET, POST | No | Request a password-reset link |
| `/reset_password/<token>` | GET, POST | No | Set a new password from the link |
| `/about` | GET | No | About page |

## Data model

**User**

| Field | Type | Notes |
|---|---|---|
| `id` | int | Primary key |
| `username` | string (20) | Unique |
| `email` | string (120) | Unique |
| `image_file` | string (20) | Avatar filename; `default.jpg` means no upload |
| `password` | string (255) | Password hash; the password itself is never stored |

**Post**

| Field | Type | Notes |
|---|---|---|
| `id` | int | Primary key |
| `title` | string (100) | |
| `content` | text | |
| `date_posted` | datetime | Indexed (the feed sorts by it) |
| `user_id` | int | Foreign key to `user.id`; indexed (user pages filter by it) |

The two are linked both ways: `user.posts` gives a user's posts, and `post.author` gives a post's author.

## How some things work

- **Passwords** are salted and hashed with Werkzeug (`generate_password_hash`). Login compares hashes.
- **Sessions:** Flask-Login stores only the user's id in a signed cookie and loads the user from the database on each request.
- **CSRF protection:** every form, including the Delete button, carries a hidden token signed with `SECRET_KEY`.
- **Ownership checks:** update and delete call `get_own_post_or_403()`, so a user can't change someone else's post even by typing the URL.
- **Password-reset tokens** are signed with `itsdangerous` and expire after 30 minutes. They include part of the current password hash, so a link stops working once the password changes.
- **The reset form doesn't reveal accounts.** It shows the same message whether or not the email exists.
- **Image uploads:** Pillow opens each upload to make sure it's a real image. It's saved under a random filename, and the user's previous picture is deleted.
- **Pagination:** `db.paginate()` fetches only one page of rows (`LIMIT`/`OFFSET`), and authors load in the same query. Pages stay fast with many posts.

## Development notes

- **Debug mode:** `main.py` runs with `debug=True`. The server reloads when files change, and crashes show Flask's interactive debugger instead of the custom 500 page. Never run with debug mode on a public server.
- **Schema changes:** there are no migrations. `db.create_all()` creates missing tables but doesn't change existing ones. After changing a model, either update `instance/site.db` by hand or delete it to start fresh (this loses data). [Flask-Migrate](https://flask-migrate.readthedocs.io/) would be the next step.
- **Shell access:** to inspect or change data:
  ```bash
  uv run flask --app main shell
  >>> db.session.execute(db.select(User)).scalars().all()
  ```

## Roadmap ideas

- Confirm a new email address before switching to it
- Show an avatar in the navbar
- Database migrations with Flask-Migrate
- Automated tests (pytest + Flask's test client)
- Search and tags for posts
