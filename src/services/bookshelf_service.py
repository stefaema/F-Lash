# src/services/bookshelf_service.py
from typing import List, Tuple, Dict, Optional
from sqlmodel import Session, select, func, col, delete
from datetime import datetime
from src.database import engine
from src.models import ActiveDeck, Deck, User

def get_user_favorites(user_id: int) -> List[Dict]:
    """
    Fetches all active decks marked as favorite by the user.
    """
    with Session(engine) as session:
        statement = (
            select(ActiveDeck, Deck)
            .join(Deck, ActiveDeck.deck_id == Deck.id)
            .where(ActiveDeck.user_id == user_id)
            .where(ActiveDeck.is_favorite == True)
            .order_by(col(ActiveDeck.last_played_at).desc())
        )
        results = session.exec(statement).all()
        return _serialize_active_decks(results)

def get_user_bookshelf(
    user_id: int, 
    page: int = 1, 
    page_size: int = 9
) -> Tuple[List[Dict], int]:
    """
    Fetches ALL active decks for the user (Paginated).
    Returns (Serialized List, Total Count).
    """
    offset = (page - 1) * page_size
    
    with Session(engine) as session:
        # 1. Total Count
        count_statement = select(func.count(ActiveDeck.id)).where(ActiveDeck.user_id == user_id)
        total_count = session.exec(count_statement).one()
        
        # 2. Fetch Data
        statement = (
            select(ActiveDeck, Deck)
            .join(Deck, ActiveDeck.deck_id == Deck.id)
            .where(ActiveDeck.user_id == user_id)
            # Order by last played (most recent first), then created date
            .order_by(col(ActiveDeck.last_played_at).desc(), col(ActiveDeck.created_at).desc())
            .offset(offset)
            .limit(page_size)
        )
        results = session.exec(statement).all()
        
        return _serialize_active_decks(results), total_count

def toggle_favorite_status(active_deck_id: int) -> bool:
    """
    Toggles the is_favorite boolean for a specific ActiveDeck.
    Returns the new state (True=Favorite, False=Not).
    """
    with Session(engine) as session:
        active_deck = session.get(ActiveDeck, active_deck_id)
        if not active_deck:
            return False
            
        active_deck.is_favorite = not active_deck.is_favorite
        session.add(active_deck)
        session.commit()
        session.refresh(active_deck)
        return active_deck.is_favorite

def _serialize_active_decks(results) -> List[Dict]:
    """Helper to format SQL results into a UI-friendly dictionary."""
    data = []
    for active_row, deck_row in results:
        # Format date safely
        last_played = "Never"
        if active_row.last_played_at:
            last_played = active_row.last_played_at.strftime("%Y-%m-%d")

        data.append({
            "active_id": active_row.id,
            "deck_id": deck_row.id,
            "title": deck_row.title,
            "description": deck_row.description,
            "front_lang": deck_row.front_language,
            "back_lang": deck_row.back_language,
            "is_favorite": active_row.is_favorite,
            "total_sessions": active_row.total_sessions_played,
            "last_played": last_played,
            "card_count": len(deck_row.cards) # Lazy load triggers here
        })
    return data

def remove_deck_from_bookshelf(user_id: int, active_deck_id: int) -> bool:
    with Session(engine) as session:
        # 1. Fetch the Active Deck ensuring it belongs to the user
        active_deck = session.exec(
            select(ActiveDeck).where(
                ActiveDeck.id == active_deck_id,
                ActiveDeck.user_id == user_id
            )
        ).first()

        if not active_deck:
            return False

        # session.exec(
        #         delete(StudyLog).where(StudyLog.active_deck_id == active_deck_id)
        #     )
            
        # 3. Delete the Active Deck itself
        session.delete(active_deck)
        
        session.commit()
        return True
