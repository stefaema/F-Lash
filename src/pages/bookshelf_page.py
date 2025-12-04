from src.core.log_manager import logger
from nicegui import ui, app, run
from math import ceil
from functools import partial
from src.pages.common import setup_page, create_navbar
from src.core.locale_manager import T
from src.services.bookshelf_service import (
    get_user_bookshelf, 
    get_user_favorites, 
    toggle_favorite_status, 
    remove_deck_from_bookshelf
)

PAGE_SIZE = 9

@ui.page('/app/my-bookshelf')
def my_bookshelf_page():
    if not setup_page(restricted=True):
        return
    create_navbar()
    ui.add_css('assets/global.css')

    # --- Security Check ---
    user_id = app.storage.user.get('id')
    if not user_id:
        ui.navigate.to('/')
        return

    # --- State ---
    current_page = 1
    
    # State container for the deck currently being processed
    deletion_state = {"id": None, "title": ""}
    
    # --- Layout Containers ---
    with ui.column().classes('w-screen min-h-screen gradient-bg overflow-auto pb-10 pt-6') as main_container:
        content_wrapper = ui.column().classes('w-full max-w-6xl mx-auto p-6 gap-8')

    # --- Async Deletion Logic ---
    async def execute_deletion():
        """
        Executed when the user clicks 'Confirm' in the dialog.
        """
        deck_id = deletion_state["id"]
        title = deletion_state["title"]
        
        if not deck_id:
            return

        delete_dialog.close()
        
        notification = ui.notification(f"Deleting '{title}'...", type='ongoing')

        print(notification)  # DEBUG: Check notification object
        try:
            # Run SQL in separate thread
            success = await run.io_bound(remove_deck_from_bookshelf, user_id, deck_id)
            
            # FIX 2: Check if notification object exists before dismissing
            if notification:
                notification.dismiss()
            
            if success:
                ui.notify(f"Successfully deleted '{title}'", type='positive')
                refresh_ui()
            else:
                ui.notify("Error: Could not delete deck.", type='negative')
                
        except Exception as e:
            # FIX 2: Check if notification object exists here as well
            if notification:
                notification.dismiss()
            logger.error(f"Deletion error: {e}")
            ui.notify("An unexpected error occurred.", type='negative')

    # --- Reusable Dialog Definition ---
    with ui.dialog() as delete_dialog, ui.card() as delete_card:
        delete_card.classes('bg-gray-900 border border-white/10')
        
        delete_title_label = ui.label().classes('text-xl font-bold text-white')
        delete_message_label = ui.label().classes('text-gray-400')
        
        with ui.row().classes('w-full justify-end gap-4 mt-6'):
            ui.button(T("cancel"), on_click=delete_dialog.close).props('flat color=white')
            ui.button(T("confirm_delete"), color='red', on_click=execute_deletion).props('raised')

    def open_delete_dialog(active_deck_id, title):
        """
        Updates the state and opens the existing dialog.
        """
        deletion_state["id"] = active_deck_id
        deletion_state["title"] = title
        
        delete_title_label.set_text(T("confirm_delete_active_deck_title", title=title))
        delete_message_label.set_text(T("confirm_delete_active_deck_message"))
        
        delete_dialog.open()

    def refresh_ui():
        """Refreshes both Favorites and Main Library lists."""
        favorites = get_user_favorites(user_id)
        all_decks, total_count = get_user_bookshelf(user_id, page=current_page, page_size=PAGE_SIZE)
        total_pages = ceil(total_count / PAGE_SIZE) if total_count > 0 else 1

        content_wrapper.clear()
        with content_wrapper:
            
            # 1. HEADER
            with ui.column().classes('w-full mb-2'):
                ui.label(T("bookshelf_page_title")).classes('text-4xl font-bold text-white')
                ui.label(T("bookshelf_page_subtitle")).classes('text-gray-400')

            # 2. FAVORITES SECTION
            if favorites:
                with ui.row().classes('items-center gap-2 mb-2'):
                    ui.icon('star', color='yellow-400').classes('text-xl')
                    ui.label(T("bookshelf_favorites_section")).classes('text-xl font-bold text-indigo-200')
                
                with ui.grid(columns='1', rows='1').classes('w-full sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8'):
                    for deck in favorites:
                        render_book_card(deck, is_favorite_list=True)
                
                ui.separator().classes('bg-white/20 mb-4')

            # 3. ALL COLLECTIONS SECTION
            with ui.row().classes('w-full justify-between items-end mb-4'):
                ui.label(T("bookshelf_general_section")).classes('text-xl font-bold text-gray-200')
                ui.label(T("page_info").format(current_page=current_page, total_pages=total_pages)).classes('text-gray-500 font-mono text-sm')

            if not all_decks:
                with ui.column().classes('w-full items-center justify-center py-12 opacity-50'):
                    ui.icon('import_contacts', size='4rem').classes('text-gray-600')
                    ui.label(T("bookshelf_no_decks")).classes('text-xl text-gray-500 mt-4')
                    ui.button(T("browse_public_library"), on_click=lambda: ui.navigate.to('/app/public-library')) \
                        .classes('mt-4 border border-indigo-500 text-indigo-300 transparent')
            else:
                with ui.grid(columns='1', rows='1').classes('w-full sm:grid-cols-2 lg:grid-cols-3 gap-6'):
                    for deck in all_decks:
                        render_book_card(deck)

                # Pagination
                if total_pages > 1:
                    with ui.row().classes('w-full justify-center gap-4 mt-8'):
                        ui.button(icon='chevron_left', on_click=lambda: change_page(-1)) \
                            .props(f'flat round color=white {"disabled" if current_page <= 1 else ""}')
                        ui.label(f"{current_page}").classes('text-white self-center font-bold text-lg')
                        ui.button(icon='chevron_right', on_click=lambda: change_page(1)) \
                            .props(f'flat round color=white {"disabled" if current_page >= total_pages else ""}')

    def render_book_card(deck, is_favorite_list=False):
        border_class = 'border-yellow-500/50' if is_favorite_list else 'border-white/10'
        bg_class = 'bg-indigo-900/20' if is_favorite_list else 'bg-black/40'

        with ui.card().classes(f'{bg_class} border {border_class} hover:border-indigo-400 transition-all duration-300 flex flex-col justify-between h-64 overflow-hidden relative group'):
            
            # --- Top: Header ---
            with ui.row().classes('w-full justify-between items-start'):
                # Lang Badge
                with ui.row().classes('items-center gap-1 bg-black/40 px-2 py-0.5 rounded text-[10px] text-gray-400 border border-white/5'):
                    ui.label(deck['front_lang'].upper())
                    ui.icon('arrow_forward', size='xs').classes('opacity-50')
                    ui.label(deck['back_lang'].upper())

                # Right: Actions
                with ui.row().classes('items-center gap-0'):
                    
                    # Favorite Toggle
                    star_icon = 'star' if deck['is_favorite'] else 'star_border'
                    star_color = 'text-yellow-400' if deck['is_favorite'] else 'text-gray-600'
                    
                    ui.button(icon=star_icon, on_click=partial(toggle_fav_handler, deck['active_id'])) \
                        .props('flat round dense') \
                        .classes(f'{star_color} hover:text-yellow-200 transition-colors z-10')
                    
                    # Options Menu
                    with ui.button(icon='more_vert').props('flat round dense').classes('text-gray-500 hover:text-white z-10'):
                        with ui.menu().classes('bg-gray-900 border border-white/10'):
                            # Menu Item: Delete
                            ui.menu_item(
                                'Remove', 
                                on_click=partial(open_delete_dialog, deck['active_id'], deck['title'])
                            ).props('active-class="bg-red-900/50 text-red-200"').classes('text-red-400 hover:bg-red-900/30')

            # --- Middle: Content ---
            with ui.column().classes('w-full gap-1 mt-2'):
                ui.label(deck['title']).classes('text-xl font-bold text-gray-100 leading-tight line-clamp-1')
                ui.label(deck['description'] or T("deck_without_description")).classes('text-xs text-gray-400 line-clamp-2 leading-snug')

            # --- Stats Row ---
            with ui.row().classes('w-full mt-auto mb-2 gap-4'):
                with ui.column().classes('gap-0'):
                    ui.label(str(deck['total_sessions'])).classes('text-lg font-bold text-indigo-300 leading-none')
                    ui.label(T("sessions")).classes('text-[10px] text-gray-500 uppercase')
                
                with ui.column().classes('gap-0'):
                    ui.label(deck['last_played']).classes('text-sm font-bold text-gray-300 leading-tight mt-1')
                    ui.label(T("last_activity")).classes('text-[10px] text-gray-500 uppercase')

            # --- Bottom: Action ---
            with ui.row().classes('w-[calc(100%+2rem)] -ml-4 -mb-4 pt-3 pb-3 px-4 border-t border-white/10 bg-black/20 justify-between items-center'):
                 ui.label(T("card_count_info").format(count=deck['card_count'])).classes('text-xs text-gray-500')
                 
                 ui.button(T("start_session"), icon="play_arrow", on_click=partial(start_session, deck['active_id'])) \
                    .props("dense color=green-7 text-color=white no-caps") \
                    .classes('shadow-lg shadow-green-900/50 px-4 font-semibold hover:scale-105 transition-transform')

    # --- Handlers ---

    def toggle_fav_handler(active_deck_id):
        logger.info(f"Toggling favorite status for ActiveDeck ID {active_deck_id}")
        new_state = toggle_favorite_status(active_deck_id)
        state_msg = T("pinned2fav") if new_state else T("removed_from_fav")
        ui.notify(state_msg, type='positive' if new_state else 'info', position='bottom')
        refresh_ui()

    def start_session(active_deck_id):
        ui.notify(T("starting_session").format(id=active_deck_id), type='positive')
        ui.navigate.to(f'/app/study?deck_id={active_deck_id}')

    def change_page(delta):
        nonlocal current_page
        current_page += delta
        refresh_ui()

    # Initial Load
    refresh_ui()
