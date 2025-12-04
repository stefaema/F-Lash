# main.py
from nicegui import ui, app
import os
import sys
from src.config import SECRET_KEY
from src.database import init_db

# Get the directory of the current file (e.g., /path/to/src)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# --- CORE MODULE IMPORTS ---
from core.locale_manager import T 
import pages.landing
import pages.auth_callback
import pages.app_page
import pages.import_json_page
import pages.public_library
import pages.bookshelf_page
import pages.study_page
# --- PATH & STYLING SETUP ---
# Determine the project root (one level up from 'src')
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Define the path to the assets folder, located in the project root
ASSETS_DIR = os.path.join(PROJECT_ROOT, 'assets') 

# Mount the 'assets' directory to be accessible at the '/assets/' URL path
if os.path.exists(ASSETS_DIR):
    app.add_static_files('/assets', ASSETS_DIR)
else:
    # Use a print statement for a critical setup issue during development
    print(f"CRITICAL ERROR: Assets directory not found at: {ASSETS_DIR}")

ui.add_css("global.css", shared=True)

# --- STARTUP ---
if __name__ in {"__main__", "__mp_main__"}:
    init_db()
    # Start the NiceGUI server
    ui.run(title=T("app_title", use_fallback=True), reload=True, port=8080, storage_secret=SECRET_KEY)
