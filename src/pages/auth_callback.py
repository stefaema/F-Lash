# src/pages/auth_callback.py
from nicegui import ui, app
from src.components.google_auth import verify_google_token
from src.core.log_manager import logger
from src.core.locale_manager import T
import asyncio
from src.services.user_service import get_or_create_user
from src.pages.common import setup_page
from src.services.user_service import AuthError

# Define a specific route for the callback
@ui.page('/auth/google/callback')
async def auth_callback_page(token: str = None):
    """
    Receives the Google Token via URL Query Parameter.
    Example: /auth/google/callback?token=eyJ...
    """
    # 1. Dark Mode & Basic Setup to avoid flash of white
    if not setup_page(restricted=False, remove_url_params= True):
        return
    
    ui.add_css('assets/global.css')
    
    # 2. Validation
    if not token:
        ui.notify("Login Error: No token provided.", type='negative')
        logger.warning("Auth callback visited without token.")
        ui.navigate.to('/')
        return

    # 3. Show a "Verifying..." spinner so user knows something is happening
    with ui.column().classes('w-screen h-screen justify-center items-center gradient-bg') as loading_container:
        ui.spinner('dots', size='xl', color='primary')
        ui.label(T("verifying_login")).classes('text-xl mt-4 animate-pulse text-white/80')

    # 4. Verify Token (Backend)
    logger.info("Received token via HTTP Redirect. Verifying...")
    user_info = await verify_google_token(token)

    if user_info:
        try:
            # 2. SYNC WITH DATABASE
            db_user = await asyncio.to_thread(get_or_create_user, user_info)
            
            # 3. SAVE TO SESSION
            app.storage.user['email'] = db_user.email
            app.storage.user['name'] = db_user.name
            app.storage.user['picture'] = db_user.picture_url
            
            # CRITICAL: Save the DB ID. We need this to link Decks/Sessions later.
            app.storage.user['id'] = db_user.id 
            
            logger.info(f"Login Complete. User ID: {db_user.id}")
            
            ui.notify(f"Welcome, {db_user.name}!", type='positive')
            ui.navigate.to('/app') 

        except AuthError as e:
            # --- Handle Whitelist Rejection --.
            logger.warning(f"Auth Blocked: {e}")
            loading_container.delete()
            with ui.column().classes('w-screen h-screen justify-center items-center gradient-bg') :
                ui.icon('block', size='64px', color='red').classes('mb-4')
                ui.label(T("whitelist_beta_blocked_user")).classes('text-xl text-white/80')


        except Exception as e:
            logger.error(f"Database Sync Error: {e}")
            ui.notify("Login failed during database sync.", type='negative')
            ui.navigate.to('/')
    else:
        logger.error("Token verification failed.")
        ui.notify("Authentication Failed.", type='negative')
        ui.navigate.to('/')
