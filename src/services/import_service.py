# src/services/import_service.py
import json
import bleach
from collections import Counter
from sqlmodel import Session, select
from src.database import engine
from src.models import Deck, Card, Tag, CardTagLink
from src.schemas import DeckImportDTO
from src.core.log_manager import logger

ALLOWED_TAGS = ['b', 'i', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li', 'code', 'pre', 'h1', 'h2', 'h3', 'blockquote', 'span']

def sanitize_html(content: str) -> str:
    if not content: return ""
    return bleach.clean(content, tags=ALLOWED_TAGS, strip=True)

def parse_and_preview_deck(file_content: str) -> dict:
    """
    1. Parses JSON.
    2. Validates Schema.
    3. Sanitizes HTML immediately (so preview shows what will be saved).
    4. Calculates Stats.
    Returns: A dict containing the 'dto' and 'stats'.
    """
    try:
        data = json.loads(file_content)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON file format.")

    try:
        deck_dto = DeckImportDTO(**data)
    except Exception as e:
        raise ValueError(f"Schema Error: {e}")

    # Sanitize content in-memory for the DTO
    for card in deck_dto.cards:
        card.front_content = sanitize_html(card.front_content)
        card.back_content = sanitize_html(card.back_content)

    # --- Generate Stats for the Confirmation Step ---
    all_tags = []
    all_sources = []
    
    for c in deck_dto.cards:
        if c.tags: all_tags.extend(c.tags)
        if c.source: all_sources.append(c.source)

    tag_counts = Counter(all_tags)
    source_counts = Counter(all_sources)

    stats = {
        "card_count": len(deck_dto.cards),
        "unique_tags": list(tag_counts.keys()),
        "top_sources": source_counts.most_common(5) # Returns [('Book A', 10), ('Web', 2)]
    }

    return {"dto": deck_dto, "stats": stats}

def save_dto_to_db(user_id: int, deck_dto: DeckImportDTO) -> str:
    """
    Takes the already validated DTO and commits it to SQL.
    """
    with Session(engine) as session:
        # A. Create Deck
        new_deck = Deck(
            owner_id=user_id,
            title=deck_dto.title,
            description=deck_dto.description,
            is_public=deck_dto.is_public
        )
        session.add(new_deck)
        session.commit()
        session.refresh(new_deck)

        # B. Process Cards
        for card_dto in deck_dto.cards:
            new_card = Card(
                deck_id=new_deck.id,
                front_content=card_dto.front_content, # Already sanitized in parse step
                back_content=card_dto.back_content,
                base_difficulty=card_dto.base_difficulty,
                source=card_dto.source
            )
            session.add(new_card)
            session.commit()
            session.refresh(new_card)

            # C. Handle Tags
            if card_dto.tags:
                for tag_name in card_dto.tags:
                    clean_tag = tag_name.strip()
                    if not clean_tag: continue
                    
                    statement = select(Tag).where(Tag.name == clean_tag)
                    tag_obj = session.exec(statement).first()
                    
                    if not tag_obj:
                        tag_obj = Tag(name=clean_tag)
                        session.add(tag_obj)
                        session.commit()
                        session.refresh(tag_obj)
                    
                    link = CardTagLink(card_id=new_card.id, tag_id=tag_obj.id)
                    session.add(link)
        
        session.commit()
        logger.info(f"Import Success: Deck '{new_deck.title}' (ID: {new_deck.id})")
        return new_deck.title
