import secrets
from typing import List
import dotenv
import os
dotenv.load_dotenv("secrets.env")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)

GOOGLE_AUTH_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_AUTH_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

_allowed_users_str = os.getenv("ALLOWED_USERS", "")
ALLOWED_USERS: List[str] = [
    email.strip() for email in _allowed_users_str.split(",") if email.strip()
]
