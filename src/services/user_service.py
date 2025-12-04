# src/services/user_service.py
from sqlmodel import Session, select
from src.database import engine
from src.models import User
from src.core.log_manager import logger
from src.config import ALLOWED_USERS

class AuthError(Exception):
    """Custom exception for authentication failures."""
    pass

def get_or_create_user(google_user_info: dict) -> User:
    """
    Checks if a user exists by email.
    If yes: Updates their name/picture (in case they changed on Google).
    If no: Creates a new record.
    Returns: The User database object.
    """
    email = google_user_info.get('email')
    name = google_user_info.get('name')
    picture = google_user_info.get('picture')

    if not email:
        raise ValueError("Cannot create user without email")
    
    if ALLOWED_USERS and email not in ALLOWED_USERS:
        logger.warning(f"Login attempt blocked for non-whitelisted user: {email}")
        raise AuthError("This email is not authorized to access the closed beta.")
    
    with Session(engine) as session:
        # 1. Try to find existing user
        statement = select(User).where(User.email == email)
        results = session.exec(statement)
        user = results.first()

        if user:
            # 2. Update existing user (Sync profile data)
            updated = False
            if user.name != name:
                user.name = name
                updated = True
            if user.picture_url != picture:
                user.picture_url = picture
                updated = True
            
            if updated:
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Updated user profile for: {email}")
            else:
                logger.info(f"User login (existing): {email}")
        
        else:
            # 3. Create new user
            user = User(
                email=email, 
                name=name, 
                picture_url=picture
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            logger.info(f"Created new user: {email}")

        return user
