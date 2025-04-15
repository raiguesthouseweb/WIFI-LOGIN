import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logger.info("Starting application...")

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)

# Setup a secret key, required by sessions
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Configure the database - Print the database URL for debugging
database_url = os.environ.get("DATABASE_URL")
logger.info(f"Database URL: {database_url}")

# Check Google credentials
creds_file_exists = os.path.exists("credentials.json")
logger.info(f"Google credentials file exists: {creds_file_exists}")
if creds_file_exists:
    logger.info(f"Credentials file path: {os.path.abspath('credentials.json')}")
    logger.info(f"Credentials file size: {os.path.getsize('credentials.json')} bytes")

if database_url:
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    
    # Initialize the app with the extension
    db.init_app(app)
    
    # Create tables if they don't exist
    with app.app_context():
        import models  # noqa: F401
        logger.info("Creating database tables if they don't exist...")
        db.create_all()
        logger.info("Database setup complete.")
else:
    logger.warning("DATABASE_URL not set, database features will be disabled")

# Import the app routes and configuration after db initialization
from app import *  # noqa: F401, F403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
