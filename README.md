---
topics:  [til-build]
---
# Today I Learned (TIL) Blog that may develop into a full weblog

A simple, fast TIL (Today I Learned) blog inspired by Simon Willison's design. This application allows you to publish quick notes and snippets you learn daily, organized by topics.

## Features

- Organized by topics- the topics accumulate as notes with named topics in the front matter add new topics; stored somehow in sqlite
- Full-text search
- Responsive design
- Markdown support with syntax highlighting
- Atom feed
- SQLite backend for simplicity

## Requirements

- Python 3.6+
- Flask
- Markdown
- A few other dependencies listed in `requirements.txt`

## Setup

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/til.git
   cd til
   ```

2. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Initialize the database:
   ```
   flask build
   ```

## Adding Content

Create directories for your topics and add Markdown files:

```
python/
  useful-list-comprehensions.md
  debugging-with-pdb.md
flask/
  flask-blueprints.md
git/
  reset-vs-revert.md
```

Each Markdown file should start with a title (a line beginning with `#`):

```markdown
# Useful List Comprehensions in Python

Here's how to use list comprehensions effectively...
```

If no title is provided, the filename (converted to title case) will be used.

## Running the App

For development:
```
flask run --debug
```

For production, use a WSGI server like Gunicorn:
```
gunicorn app:app
```

## Deployment

This app is designed to be simple to deploy. You can deploy it to any platform that supports Python applications, such as:

- Heroku
- PythonAnywhere
- Vercel
- Fly.io
- VPS with Nginx and Gunicorn

### Example deployment with Fly.io

1. Install the Fly CLI
2. Create a `fly.toml` file
3. Deploy with `fly deploy`

## Customization

- Edit `templates/` to change the HTML structure
- Modify `static/styles.css` to change the appearance
- Update author information in `feed.py`

## License

MIT

## Acknowledgements

Inspired by [Simon Willison's TIL](https://til.simonwillison.net/)
