# src/schemas.py
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, TypedDict

class CardImportDTO(BaseModel):
    front_content: str
    back_content: str
    tags: Optional[List[str]] = Field(default_factory=list)
    base_difficulty: Optional[int] = 3
    source: Optional[str] = None

class DeckImportDTO(BaseModel):
    title: str
    description: Optional[str] = ""
    is_public: bool = False
    cards: List[CardImportDTO]

    @field_validator('cards')
    def validate_card_count(cls, v):
        if not v:
            raise ValueError("Deck must contain at least one card.")
        if len(v) > 500:
            raise ValueError("Max 500 cards per import allowed.")
        return v

class SessionStats(TypedDict):
    correct: int
    wrong: int
    combo: int
    mistakes: Dict[str, int]  # {"card_id": count}

class SessionState(TypedDict):
    """
    The 'Hot State' stored in app.storage.user.
    It tracks the Master Queue and the Server's cursor position.
    """
    deck_id: int
    
    # All Card IDs for this run, in order.
    queue: List[int]
    
    # "Server Anchor".
    # Tracks how many cards have been dispensed (buffered) to the frontend.
    # We use this to know where to slice the queue for the NEXT batch request.
    fetch_index: int 
    
    stats: SessionStats
    
    # Timestamp string (ISO format) for analytics later
    start_time: str
