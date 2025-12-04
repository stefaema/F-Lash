from nicegui import ui, app
from math import ceil
from src.pages.common import setup_page, create_navbar
from src.core.locale_manager import T
from src.services.deck_service import get_public_decks, activate_deck, is_already_active

# Constants
PAGE_SIZE = 9

# We don't need the global handle_add_deck anymore, 
# logic is moved inside render_deck_card to access UI elements

@ui.page('/app/public-library')
def public_library_page():
    if not setup_page(restricted=True):
        return
    create_navbar()
    ui.add_css('assets/global.css')
    
    # --- UI State ---
    current_page = 1
    
    # Containers
    with ui.column().classes('w-screen h-screen gradient-bg overflow-auto pb-10 pt-6') as page_container:
            content_area = ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-6')
    
    def refresh_grid():
        """Reloads the grid based on current_page."""       
        decks, total_count = get_public_decks(page=current_page, page_size=PAGE_SIZE)
        total_pages = ceil(total_count / PAGE_SIZE) if total_count > 0 else 1
        
        with page_container:
            content_area.clear()
            with content_area:
                # -- Header --
                with ui.row().classes('w-full justify-between items-end mb-4'):
                    with ui.column().classes('gap-1'):
                        ui.label(T("public_library_page_title")).classes('text-4xl font-bold text-white')
                        ui.label(T("public_library_page_subtitle")).classes('text-gray-400')
                    ui.label(T("page_info", current_page=current_page, total_pages=total_pages)).classes('text-gray-500 font-mono text-sm')

                # -- Grid --
                if not decks:
                    with ui.column().classes('w-full items-center justify-center py-20 opacity-50'):
                        ui.icon('sentiment_dissatisfied', size='4rem').classes('text-gray-600')
                        ui.label(T("no_public_decks_found")).classes('text-xl text-gray-500 mt-4')
                else:
                    with ui.grid(columns='1', rows='1').classes('w-full sm:grid-cols-2 lg:grid-cols-3 gap-6'):
                        for deck in decks:
                            render_deck_card(deck)
                
                # -- Pagination Controls --
                if total_pages > 1:
                    with ui.row().classes('w-full justify-center gap-4 mt-8'):
                        ui.button(icon='chevron_left', on_click=lambda: change_page(-1)) \
                            .props(f'flat round color=white {"disabled" if current_page <= 1 else ""}')
                        
                        # (Pagination logic omitted for brevity, same as your code)
                        ui.label(f"{current_page} / {total_pages}").classes('text-white self-center') # Simplified for snippet

                        ui.button(icon='chevron_right', on_click=lambda: change_page(1)) \
                            .props(f'flat round color=white {"disabled" if current_page >= total_pages else ""}')

    def render_deck_card(deck):
        """Renders a single deck card."""
        with ui.card().classes('bg-black/40 border border-white/10 hover:border-indigo-500/80 transition-all duration-300 flex flex-col justify-between h-64 overflow-hidden relative group'):
            
            # --- Top Section ---
            with ui.column().classes('w-full gap-2'):
                with ui.row().classes('w-full justify-between items-start'):
                    # Languages Badge
                    with ui.row().classes('items-center gap-1 bg-white/5 px-2 py-0.5 rounded text-xs text-indigo-300 border border-white/5'):
                        ui.label(deck['front_lang'].upper())
                        ui.icon('arrow_forward', size='xs').classes('opacity-50')
                        ui.label(deck['back_lang'].upper())

                    ui.label(f"ID: {deck['id']}").classes('text-[10px] text-gray-600 italic font-mono')
                    ui.label(deck['timestamp']).classes('text-[10px] text-gray-600 italic font-mono')

                ui.label(deck['title']).classes('text-xl font-bold text-gray-100 leading-tight line-clamp-1')
                ui.label(deck['description'] or "No description provided.").classes('text-sm text-gray-400 line-clamp-3 leading-snug')

            # --- Bottom Section ---
            with ui.column().classes('w-full gap-3 mt-auto'):
                
                # Metadata (Stats)
                with ui.row().classes('w-full items-center gap-4 text-xs text-gray-500'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('style', size='xs')
                        ui.label(T("card_count_info", count=deck['card_count']))
                    
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('person', size='xs')
                        ui.label(deck['author']).classes('truncate max-w-[100px]')

                # --- Dynamic Action Button Container ---
                # We define a container specifically for the button/label area
                with ui.row().classes('w-[calc(100%+2rem)] -ml-4 -mb-4 pt-3 pb-3 px-4 border-t border-white/10 bg-black/20 justify-end items-center') as action_container:
                    
                    def render_already_added():
                        """Helper to render the static label."""
                        ui.label("Already in Bookshelf").classes('text-sm text-green-400 italic')

                    def on_add_click():
                        """Local handler that has access to 'action_container'."""
                        user_id = app.storage.user.get('id')
                        if not user_id:
                            ui.notify("Please login first", type='warning')
                            return

                        # 1. Call Backend
                        success = activate_deck(user_id, deck['id'])
                        
                        if success:
                            ui.notify(T("added_successfully2bookshelf"), type='positive')
                            
                            # 2. Dynamic Update: Clear the container and render the label
                            action_container.clear()
                            with action_container:
                                render_already_added()
                        else:
                            ui.notify(T("error_adding_deck2bookshelf"), type='negative')

                    # Initial Render Logic
                    if is_already_active(app.storage.user.get('id'), deck['id']):
                        render_already_added()
                    else:
                        ui.button(T("add_to_bookshelf"), icon="bookmark_add", on_click=on_add_click) \
                            .props("flat dense color=indigo no-caps") \
                            .classes('text-sm font-semibold hover:bg-indigo-500/10 px-3 rounded')

    # --- Event Handlers ---
    def change_page(delta):
        nonlocal current_page
        current_page += delta
        refresh_grid()

    def set_page(page_num):
        nonlocal current_page
        current_page = page_num
        refresh_grid()

    # Initial Load
    refresh_grid()
