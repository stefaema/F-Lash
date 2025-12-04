# src/database.py
from sqlmodel import SQLModel, create_engine, Session
import os

# Define the database file path (in the root directory)
DB_FILE = "db/study_app.db"
DATABASE_URL = f"sqlite:///{DB_FILE}"

# Create the engine
# check_same_thread=False is needed for SQLite with NiceGUI/FastAPI concurrency
engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})

def init_db():
    """
    Creates the database tables based on the models.
    Should be called on app startup.
    """
    from src.models import User, Deck, Card, ActiveDeck # Import to register models
    SQLModel.metadata.create_all(engine)
    print(f"Database initialized at {DB_FILE}")

def get_db_session():
    """
    Yields a database session. 
    Use with context manager: `with get_db_session() as session:`
    """
    with Session(engine) as session:
        yield session

# Direct session factory for when generators aren't suitable
def create_session():
    return Session(engine)
