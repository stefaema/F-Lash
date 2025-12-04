from nicegui import app, ui
from src.core.locale_manager import T
def setup_page(restricted: bool = True, remove_url_params: bool = False) -> bool:
    ui.dark_mode() # Enable dark mode globally. For now, we keep it here.
    ui.add_head_html("<style>html, #c3 { padding: 0 !important;}</style>") # Remove default padding from html and #c3
    if restricted:
        # If the page is restricted, check for user session
        if not app.storage.user.get('id'):
            ui.notify(T("access_denied_login_required"), type='negative')
            ui.navigate.to('/')
            return False
    
    if remove_url_params:
        ui.run_javascript("window.history.replaceState(null, '', window.location.pathname);")
    
    return True

def create_navbar():
    with ui.header().classes('w-full bg-black text-white justify-between items-center px-6 py-2 shadow-md'):
        
        with ui.row().classes('items-center gap-4'):
            with ui.button(icon='menu').props('flat round color=white'):
                with ui.menu().props('auto-close'):
                    ui.menu_item(T("home"), on_click=lambda: ui.navigate.to('/app'))
                    ui.menu_item(T("public_library"), on_click=lambda: ui.navigate.to('/app/public-library'))
                    ui.menu_item(T("my_bookshelf"), on_click=lambda: ui.navigate.to('/app/my-bookshelf'))
                    ui.menu_item(T("deck_editor"), on_click=lambda: ui.navigate.to('/app/import-json'))

            ui.label(T("app_title")).classes('text-xl font-bold tracking-tight')

        with ui.row().classes('items-center gap-4'):
            ui.button(icon='settings', on_click=lambda: ui.notify('Settings')).props('flat round color=white')
            
            with ui.avatar(size='32px').classes('bg-gray-700 cursor-pointer'):
                # If you have an image, use ui.image inside, but ensure it fits
                if app.storage.user.get("picture"):
                    ui.image(app.storage.user.get("picture"))
                else:
                    ui.icon('person') # Fallback icon if no image

                with ui.menu().props('auto-close'):
                    ui.menu_item('Logout', on_click=lambda: ui.navigate.to('/'))
