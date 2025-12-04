from nicegui import ui
import os
from typing import Optional
from src.pages.common import setup_page
from src.components.google_auth import GoogleSignInButton, verify_google_token
from core.locale_manager import T
from core.log_manager import logger

@ui.page('/')
def landing_page():
    if not setup_page(restricted=False):
        return

    ui.add_head_html('<script src="https://accounts.google.com/gsi/client" async defer></script>')
    ui.add_head_html('<script src="/assets/js/google_auth_handler.js"></script>')
    # Load our custom CSS
    ui.add_css('assets/global.css')
    ui.add_css('assets/landing.css')

    async def handle_google_login(token: str):
        """
        Called when the component successfully extracts the token.
        """
        if not token:
            ui.notify("Login failed: No token received", type='negative')
            return

        # Verify on backend
        user_info = await verify_google_token(token)
        
        if user_info:
            email = user_info.get('email')
            name = user_info.get('name')
            
            ui.notify(f"Welcome, {name}!", type='positive')
            logger.info(f"User logged in: {email}")
            
            # Example: Redirect to dashboard
            # ui.navigate.to('/dashboard')
        else:
            ui.notify("Authentication Failed", type='negative')
            logger.error("Authentication failed during token verification")

    #Root Container (gradient, fullscreen, card centered)
    with ui.column().classes('w-screen h-screen gradient-bg overflow-hidden justify-center items-center'):

        ui.image('/assets/images/glob.png').classes('glob')
        # Centered Content Container
        with ui.card().classes("justify-left transparent shadow-none max-w-4xl w-full p-10"):
            # Left Side: Text Content
            with ui.column().classes('max-w-xxl gap-6'):
                ui.label(T("app_title")).classes('app-title')
                ui.label(T("app_subtitle")).classes('app-subtitle')
                ui.label(T("app_description")).classes('text-white/75 italic max-w-lg text-lg')
                ui.label(T("app_qualities")).classes('app-subtitle')
                # Sign-In Button
                with ui.column().classes('items-center backdrop-blur-md bg-black/30 p-6 mt-4 w-full rounded-xl') as login_section:
                    GoogleSignInButton(on_auth_success=handle_google_login)
                    ui.label(T("login_disclaimer")).classes('text-white/60 text-s max-w-md border-t border-white/20 pt-2 mt-2')


