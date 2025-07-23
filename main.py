from app import create_app
import os
from dotenv import load_dotenv
from app.Executable_Scripts.run_facebook import execute_facebook

load_dotenv()  # Carfar desde ENV

# Create the Flask app first
app = create_app()

with app.app_context():
    # Run the Facebook scraper 
    execute_facebook()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090, debug=True)
