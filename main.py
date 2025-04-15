import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)

# Setup a secret key, required by sessions
app.secret_key = os.environ.get("SESSION_SECRET", "default_secret_key_for_development")

# Configure the database - Print the database URL for debugging
database_url = os.environ.get("DATABASE_URL")
print(f"Database URL: {database_url}")

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
        db.create_all()
else:
    print("WARNING: DATABASE_URL not set, database features will be disabled")

# Import the app routes and configuration after db initialization
from app import *  # noqa: F401, F403

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
