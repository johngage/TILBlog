# test_dark_mode.py
def test_dark_mode_toggle_exists():
    """Test that the dark mode toggle exists in the base template."""
    # Import your Flask app
    from app import app
    
    # Create a test client
    client = app.test_client()
    
    # Get the homepage
    response = client.get('/')
    
    # Check that the response contains the dark mode toggle
    assert response.status_code == 200
    assert 'id="dark-mode-toggle"' in response.data.decode('utf-8')

def test_dark_mode_toggle_functionality():
    """Test that the dark mode JS is included."""
    from app import app
    client = app.test_client()
    response = client.get('/')
    
    # Check for the JavaScript that handles dark mode
    assert 'dark-mode.js' in response.data.decode('utf-8')