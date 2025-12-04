from nicegui import ui
from src.config import GOOGLE_AUTH_CLIENT_ID
from google.oauth2 import id_token
import asyncio
from google.auth.transport import requests as google_requests
from src.core.log_manager import logger

_google_request = google_requests.Request()

async def verify_google_token(token: str):
    """Verifies the Google JWT asynchronously."""
    try:
        id_info = await asyncio.to_thread(
            id_token.verify_oauth2_token,
            token, 
            _google_request, 
            GOOGLE_AUTH_CLIENT_ID
        )
        return id_info
    except ValueError as e:
        logger.error(f"Token verification failed: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected auth error: {e}")
        return None

class GoogleSignInButton(ui.element):
    def __init__(self, on_auth_success: callable = None):
        """
        Renders the Google Sign-In Button.
        Note: on_auth_success is handled by the callback page.
        """
        super().__init__('div')
        
        # We only need a target for the button to render
        self.target_id = f'g-signin-{self.id}'
        
        with self:
            ui.element('div').props(f'id={self.target_id}')
        
        # Initialize JS - No complex binding needed
        ui.timer(0.1, self._init_client_side, once=True)

    def _init_client_side(self):
        # We pass 0 as componentId because we don't use it anymore
        cmd = f'initGoogleLogin("{GOOGLE_AUTH_CLIENT_ID}", "{self.target_id}")'
        ui.run_javascript(cmd)
