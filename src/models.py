from typing import Optional, List
from datetime import datetime, timezone
from enum import IntEnum
from sqlmodel import SQLModel, Field, Relationship
import json

class Difficulty(IntEnum):
    """
    Static difficulty rating set by the deck creator.
    """
    EASIEST = 1
    EASY = 2
    MEDIUM = 3
    HARD = 4
    HARDEST = 5

# --- JOIN TABLES (Many-to-Many) ---

class CardTagLink(SQLModel, table=True):
    """
    Link table to allow one Card to have multiple Tags,
    and one Tag to belong to multiple Cards.
    """
    tag_id: Optional[int] = Field(default=None, foreign_key="tag.id", primary_key=True)
    card_id: Optional[int] = Field(default=None, foreign_key="card.id", primary_key=True)

# --- 1. STATIC CONTENT (The Book) ---

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str
    picture_url: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    owned_decks: List["Deck"] = Relationship(back_populates="owner")
    active_decks: List["ActiveDeck"] = Relationship(back_populates="user")

class Deck(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id")
    
    title: str
    description: Optional[str] = None
    is_public: bool = Field(default=False)
    version: int = Field(default=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    front_language: str = Field(default="en", description="ISO code for front side")
    back_language: str = Field(default="en", description="ISO code for back side")

    # Relationships
    owner: User = Relationship(back_populates="owned_decks")
    cards: List["Card"] = Relationship(back_populates="deck")
    active_instances: List["ActiveDeck"] = Relationship(back_populates="deck")

class Tag(SQLModel, table=True):
    """
    Represents a category label (e.g., 'Anatomy', 'Exam 1', 'Geo:Asia').
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, unique=True) 
    
    # Relationships
    cards: List["Card"] = Relationship(back_populates="tags", link_model=CardTagLink)

class Card(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    deck_id: int = Field(foreign_key="deck.id")
    
    front_content: str 
    back_content: str   
    base_difficulty: int = Field(default=Difficulty.MEDIUM.value)
    source: Optional[str] = Field(default=None)

    # Relationships
    deck: Deck = Relationship(back_populates="cards")
    
    tags: List[Tag] = Relationship(back_populates="cards", link_model=CardTagLink)

# --- 2. USER LIBRARY (The Save File) ---

class ActiveDeck(SQLModel, table=True):
    """
    Represents the User's copy of a Deck.
    Stores high-level stats.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    deck_id: int = Field(foreign_key="deck.id")
    
    is_favorite: bool = Field(default=False)
    total_sessions_played: int = Field(default=0)
    last_played_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user: User = Relationship(back_populates="active_decks")
    deck: Deck = Relationship(back_populates="active_instances")


