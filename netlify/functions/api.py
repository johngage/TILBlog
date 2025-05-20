from flask import Flask
import sys, os
# Import serverless adapter 
from serverless_wsgi import handle_request

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Import your app
from app import app

def handler(event, context):
    return handle_request(app, event, context)