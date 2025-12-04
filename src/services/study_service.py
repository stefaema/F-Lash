# src/services/study_service.py
from typing import List, Tuple, Optional, Dict
from datetime import datetime, timezone
import random
import json
from src.core.log_manager import logger

from nicegui import app
from sqlmodel import Session, select
from src.database import engine
from src.models import Card, ActiveDeck, CardTagLink
from src.schemas import SessionState  # Assumed to be defined in schemas.py

# --- CONSTANTS ---
SESSION_KEY = 'active_study_session'
DEFAULT_BATCH_SIZE = 5

# --- FILTERING LOGIC ---

def _fetch_session_candidates(
    active_deck_id: int, 
    difficulty_range: Tuple[int, int] = (1, 5), 
    tag_ids: Optional[List[int]] = None,
    shuffle: bool = True
) -> List[int]:
    """
    Internal helper: Generates the List of Card IDs for the study session. This applies the user-defined filters.
    Returns: List of Card IDs.
    """
    with Session(engine) as session:
        # 1. Validate Deck Ownership via ActiveDeck
        active_deck = session.get(ActiveDeck, active_deck_id)
        if not active_deck:
            raise ValueError("Active Deck not found.")
            
        # 2. Build Query
        query = select(Card.id).where(Card.deck_id == active_deck.deck_id)
        
        # 3. Filter: Difficulty
        min_diff, max_diff = difficulty_range
        query = query.where(Card.base_difficulty >= min_diff)
        query = query.where(Card.base_difficulty <= max_diff)
        
        # 4. Filter: Tags (Optional)
        if tag_ids:
            query = query.join(CardTagLink).where(CardTagLink.tag_id.in_(tag_ids))
        
        # 5. Execute
        results = session.exec(query).all()
        # Deduplicate results (in case joins created duplicates)
        card_ids = list(set(results))

        # 6. Order/Shuffle
        if shuffle:
            random.shuffle(card_ids)
        else:
            card_ids.sort() # Deterministic order if not shuffled
            
        return card_ids

# --- SESSION LIFECYCLE (Set/Reset) ---

def initialize_session(
    active_deck_id: int,
    difficulty_range: Tuple[int, int],
    tag_ids: List[int],
    shuffle: bool
) -> int:
    """
    Initializes the Game State in app.storage.user.
    Returns: Total number of cards in the queue.
    """
    # 1. Generate the Queue
    queue = _fetch_session_candidates(active_deck_id, difficulty_range, tag_ids, shuffle)

    if not queue:
        raise ValueError("No cards match the selected filters.")
    logger.info(f"Initialized session with {len(queue)} cards for ActiveDeck ID {active_deck_id} using filters: difficulty_range={difficulty_range}, tag_ids={tag_ids}, shuffle={shuffle}")

    # 2. Construct the State Object (TypedDict)
    new_state: SessionState = {
        "deck_id": active_deck_id,
        "start_time": datetime.now(timezone.utc).isoformat(),
        
        # The Map
        "queue": queue,
        "initial_count": len(queue),
        
        # server-side cursor: How many cards have we sent to the client?
        "fetch_index": 0,
        
        # Stats
        "stats": {
            "correct": 0,
            "wrong": 0,
            "combo": 0,
            "mistakes": {}
        }
    }
    
    # 3. Persist to Cookie-Storage
    app.storage.user[SESSION_KEY] = new_state
    
    return len(queue)

def clear_session():
    """Removes the current session from storage."""
    if SESSION_KEY in app.storage.user:
        del app.storage.user[SESSION_KEY]

# --- BATCH FETCHING ---

def get_next_batch(batch_size: int = DEFAULT_BATCH_SIZE) -> List[Card]:
    """
    Fetches the next N cards from the queue based on fetch_index.
    Minimizes DB calls by buffering.
    """
    state: SessionState = app.storage.user.get(SESSION_KEY)
    if not state:
        logger.warning("No active study session found when fetching next batch.")
        return []

    # 1. Determine Slice
    queue = state['queue']
    start_idx = state['fetch_index']
    
    if start_idx >= len(queue):
        logger.warning("Fetch index beyond queue length; no more cards to fetch.")
        return []

    end_idx = start_idx + batch_size
    
    if end_idx > len(queue):
        logger.info("Adjusting batch size to fit remaining cards in queue.")
        end_idx = len(queue)

    batch_ids = queue[start_idx : end_idx]
    
    if not batch_ids:
        logger.warning("No batch IDs found in the specified range; returning empty list. This should not happen if the queue and fetch_index are managed correctly.")
        return []

    # 2. Bulk Fetch Content
    with Session(engine) as session:
        statement = select(Card).where(Card.id.in_(batch_ids))
        cards = session.exec(statement).all()
        
        # Re-order results to match the queue order (SQL 'IN' does not guarantee order)
        card_map = {c.id: c for c in cards}
        ordered_cards = [card_map[uid] for uid in batch_ids if uid in card_map]

    # 3. Update Cursor
    state['fetch_index'] += len(ordered_cards)
    app.storage.user[SESSION_KEY] = state
    
    logger.info(f"Fetched batch of {len(ordered_cards)} cards; updated fetch_index to {state['fetch_index']}. Initial index range was {start_idx}-{end_idx}.")

    return ordered_cards

# --- STATE MUTATION (Gameplay Updates) ---

def update_session_state(card_id: int, result: str):
    """
    Updates the session stats based on user action.
    result: 'KNOW' | 'MISS' | 'DISCARD'
    """
    state: SessionState = app.storage.user.get(SESSION_KEY)
    if not state: return

    if result == 'KNOW':
        state['stats']['correct'] += 1
        state['stats']['combo'] += 1
        
    elif result == 'MISS':
        state['stats']['wrong'] += 1
        state['stats']['combo'] = 0
        
        # Increment mistake count for this card
        sid = str(card_id)
        state['stats']['mistakes'][sid] = state['stats']['mistakes'].get(sid, 0) + 1
        
        # Move the failed card to the end of the queue so it appears again. There was a weird note here. If something breaks, check the logic.
        state['queue'].append(card_id)
        
    elif result == 'DISCARD':
        # Just ignore it, stats don't change, card is effectively consumed
        pass

    app.storage.user[SESSION_KEY] = state

def finalize_session() -> bool:
    """
    Called when queue is empty or user quits.
    Writes the SessionLog to the Database.
    """
    clear_session()

