# src/services/deck_service.py
from nicegui import ui, app
from typing import List, Tuple, Optional, Dict
from sqlmodel import Session, select, func, col
from src.database import engine
from src.models import CardTagLink, Deck, Tag, User, ActiveDeck, Card
def get_public_decks(
    page: int = 1, 
    page_size: int = 9
) -> Tuple[List[dict], int]:
    """
    Retrieves a paginated list of public decks.
    Returns:
        Tuple containing:
        1. List of dicts with deck details and author name.
        2. Total count of public decks (for pagination math).
    """
    offset = (page - 1) * page_size
    
    with Session(engine) as session:
        # 1. Get Total Count (for pagination UI)
        count_statement = select(func.count(Deck.id)).where(Deck.is_public == True)
        total_count = session.exec(count_statement).one()
        
        # 2. Get Data (Deck + Author Name)
        # We join User to display the author's name without N+1 queries
        statement = (
            select(Deck, User.name)
            .join(User, Deck.owner_id == User.id)
            .where(Deck.is_public == True)
            .order_by(col(Deck.created_at).desc())
            .offset(offset)
            .limit(page_size)
        )
        
        results = session.exec(statement).all()
        
        # 3. Serialize to a friendly format
        deck_list = []
        for deck, author_name in results:
            deck_list.append({
                "id": deck.id,
                "title": deck.title,
                "description": deck.description,
                "author": author_name,
                "timestamp": deck.created_at.strftime("%Y-%m-%d"),
                "front_lang": deck.front_language,
                "back_lang": deck.back_language,
                "card_count": len(deck.cards), # Note: Accessing relationship triggers lazy load
                "created_at": deck.created_at
            })
            
        return deck_list, total_count


def activate_deck(user_id: int, deck_id: int) -> bool:
    """
    Activates a deck for a user (Adds to bookshelf).
    
    1. Checks if deck exists.
    2. Checks if already active (prevents duplicates).
    3. Creates ActiveDeck entry.
    """
    with Session(engine) as session:
        # 1. Check if Deck exists
        deck = session.get(Deck, deck_id)
        if not deck:
            return False

        # 2. Check if already active (Idempotency)
        # We don't want to wipe progress if they click "Add" again.
        statement = select(ActiveDeck).where(
            ActiveDeck.user_id == user_id,
            ActiveDeck.deck_id == deck_id
        )
        existing_active_deck = session.exec(statement).first()
        
        if existing_active_deck:
            return True # It is active, so operation is a "success"

        # 3. Create the ActiveDeck container
        new_active_deck = ActiveDeck(
            deck_id=deck.id, 
            user_id=user_id,
            is_favorite=False
        )
        session.add(new_active_deck)
        session.commit()
        session.refresh(new_active_deck)
        
        session.commit()
        return True

def is_already_active(user_id: int, deck_id: int) -> bool:
    """
    Checks if a deck is already active for a user.
    """
    with Session(engine) as session:
        statement = select(ActiveDeck).where(
            ActiveDeck.user_id == user_id,
            ActiveDeck.deck_id == deck_id
        )
        existing_active_deck = session.exec(statement).first()
        
        return existing_active_deck is not None

def get_study_metadata(user_id: int, active_deck_id: int) -> Optional[Dict]:
    """
    Validates ownership of an ActiveDeck and retrieves title and available tags.
    Returns None if unauthorized or not found.
    """
    with Session(engine) as session:
        # 1. Fetch & Validate Ownership
        active_deck = session.get(ActiveDeck, active_deck_id)
        
        if not active_deck or active_deck.user_id != user_id:
            return None

        # 2. Fetch Unique Tags for Filter
        tag_query = (
            select(Tag)
            .join(CardTagLink)
            .join(Card)
            .where(Card.deck_id == active_deck.deck_id)
            .distinct()
        )
        tags = session.exec(tag_query).all()
        
        return {
            "title": active_deck.deck.title,
            "tags": {t.id: t.name for t in tags}
        }
