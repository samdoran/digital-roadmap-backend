import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_NAME = os.getenv("SQLALCHEMY_DB", "release_notes_db")
DB_USER = os.getenv("SQLALCHEMY_USER", "postgres")
DB_PASSWORD = os.getenv("SQLALCHEMY_PASSWORD", "password")
SQLALCHEMY_DATABASE_URI = f"postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@localhost/{DB_NAME}"
