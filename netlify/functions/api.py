from flask import Flask
from flask_serverless import serverless_wsgi
import sys
import os

# Add the root directory to the path so we can import the app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import your app
from app import app

# Handle serverless function
def handler(event, context):
    return serverless_wsgi.handle(app, event, context)