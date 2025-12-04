from nicegui import ui, app, events
import os
from src.core.locale_manager import T
from src.core.log_manager import logger
from src.pages.common import setup_page, create_navbar
from src.services.import_service import parse_and_preview_deck, save_dto_to_db

@ui.page('/app/import-json')
def import_json_page():
    if not setup_page(restricted=True):
        return
    create_navbar()
    ui.add_css('assets/global.css')
    ui.add_head_html('''
        <style>
            .q-markdown pre {
                white-space: pre-wrap !important;       /* Wraps code lines */
                word-break: break-word !important;      /* Breaks long words if needed */
                background: rgba(0, 0, 0, 0.3);         /* Optional: Darker bg for code */
                padding: 1rem;
                border-radius: 0.5rem;
            }
        </style>
    ''')

    # --- STATE ---
    # We store the DTO here temporarily to pass it from Step 2 -> Step 3
    current_import_data = {"dto": None} 

    async def handle_parsing(e: events.UploadEventArguments, stepper_element):
        """Step 2 -> Step 3: Parse File & Show Preview"""
        try:
            content = await e.file.text()
            # 1. Parse & Stats
            result = parse_and_preview_deck(content)
            dto = result['dto']
            stats = result['stats']
            
            # Save to state for the next step
            current_import_data['dto'] = dto

            # 2. Build the Review UI (Step 3)
            review_container.clear()
            with review_container:
                # -- HEADER --
                ui.label(T("review_deck_details")).classes('text-2xl font-bold text-indigo-300')
                
                with ui.card().classes('w-full bg-black/20 border border-white/10 p-4 mt-2'):
                    with ui.row().classes('w-full justify-between items-center'):
                        with ui.column().classes('gap-1'):
                            ui.label(dto.title).classes('text-xl font-bold')
                            ui.label(dto.description).classes('text-gray-400 italic text-sm')
                        
                        # Badge: Card Count
                        with ui.row().classes('items-center bg-indigo-500/20 px-3 py-1 rounded-full border border-indigo-500/50'):
                            ui.icon('style', size='xs').classes('mr-2')
                            ui.label(f"{stats['card_count']} Cards").classes('font-bold')

                # -- STATS GRID --
                with ui.grid(columns=2).classes('w-full gap-4 mt-4'):
                    # Col 1: Tags
                    with ui.column().classes('p-3 bg-black/20 rounded-lg border border-white/10'):
                        ui.label("Detected Tags").classes('text-xs text-gray-400 uppercase font-bold tracking-wider mb-2')
                        if stats['unique_tags']:
                            with ui.row().classes('gap-2 wrap'):
                                for tag in stats['unique_tags']:
                                    ui.label(tag).classes('px-2 py-1 bg-white/10 rounded text-xs text-indigo-200')
                        else:
                            ui.label("No tags found").classes('text-gray-600 italic text-sm')

                    # Col 2: Sources
                    with ui.column().classes('p-3 bg-black/20 rounded-lg border border-white/10'):
                        ui.label("Top Sources").classes('text-xs text-gray-400 uppercase font-bold tracking-wider mb-2')
                        if stats['top_sources']:
                            with ui.column().classes('gap-1'):
                                for src, count in stats['top_sources']:
                                    with ui.row().classes('w-full justify-between text-sm'):
                                        ui.label(src if src else "Unknown").classes('truncate w-32 text-gray-300')
                                        ui.label(f"x{count}").classes('text-gray-500')
                        else:
                            ui.label("No sources found").classes('text-gray-600 italic text-sm')

                # -- COLLAPSIBLE PREVIEW --
                with ui.expansion(f"View all {stats['card_count']} Cards", icon="visibility").classes('w-full mt-4 bg-black/20 rounded-lg border border-white/10').props("header-class='text-indigo-300'"):
                     with ui.scroll_area().classes('h-64 w-full preview-scroll p-2'):
                         with ui.column().classes('gap-2 w-full'):
                             for i, card in enumerate(dto.cards, 1):
                                 with ui.row().classes('w-full items-start p-2 bg-black/30 rounded border border-white/5'):
                                     ui.label(f"#{i}").classes('text-gray-500 text-xs mt-1 mr-2 w-6')
                                     with ui.column().classes('w-full'):
                                         # Truncate long text for preview
                                         front_preview = (card.front_content[:75] + '...') if len(card.front_content) > 75 else card.front_content
                                         ui.markdown(front_preview).classes('text-sm text-gray-200')

            ui.notify(T("import_json_step2_success", deck_title=dto.title, card_count=len(dto.cards)), type='positive')
            stepper_element.next() # Go to Step 3

        except ValueError as err:
            ui.notify(str(err), type='warning')
        except Exception as err:
            logger.error(f"Parse Error: {err}")
            ui.notify("Error parsing file", type='negative')

    async def finalize_import(stepper_element):
        """Step 3 -> Step 4: Save to DB"""
        if not current_import_data['dto']:
            return

        user_id = app.storage.user.get('id')
        try:
            deck_title = save_dto_to_db(user_id, current_import_data['dto'])
            ui.notify(f"Success! Imported '{deck_title}'", type='positive')
            stepper_element.next() # Go to Step 4
        except Exception as e:
            ui.notify(f"Database Error: {e}", type='negative')

    with ui.column().classes('w-screen min-h-screen gradient-bg text-white p-8 overflow-y-auto overflow-x-auto'):
        
        with ui.column().classes('w-full items-center text-center max-w-3xl mx-auto mb-10'):
            ui.label(T("import_json_page_title")).classes('text-5xl font-extrabold text-white mt-12')
            ui.label(T("import_json_page_subtitle")).classes('text-xl text-gray-400 mt-2')

        # --- Horizontal Separator ---
        ui.separator().classes('w-1/2 mx-auto bg-white/70 mb-10')

        with ui.card().classes('max-w-1/2 bg-black/30 p-6 rounded-xl shadow-2xl border border-indigo-600/50 hover:border-indigo-500 transition-all duration-300 mx-auto overflow-x-auto'):
            with ui.stepper().props("vertical done-color='green'").classes('w-full max-w-3xl mx-auto transparent') as stepper:

                with ui.step("import_json_step1", T("import_json_step_1_title")).classes('text-lg text-gray-300 leading-relaxed'):
                    ui.markdown(T("import_json_step_1_desc")).classes('text-lg text-gray-300 leading-relaxed')
                    ui.markdown(T("import_json_step_1_formatting_guidelines")).classes('w-full text-lg text-gray-300 leading-relaxed overflow-x-auto break-words')
                    with ui.row().classes('justify-center items-center w-full'):
                        ui.button(T("download_sample_json"), on_click=lambda: ui.download('/assets/samples/sample_deck.json', 'sample_deck.json'), icon="download").classes('mt-4 border border-indigo-500 hover:border-indigo-400 transparent')
                        ui.button(T("next_step"), on_click = lambda: stepper.next(), icon="arrow_downward").classes('mt-4 ml-4 border border-green-500 hover:border-green-400 transparent')
                
                with ui.step("import_json_step2", T("import_json_step_2_title")).classes('text-md text-gray-300 leading-relaxed'):
                    ui.markdown(T("import_json_step_2_desc")).classes('text-lg text-gray-300 leading-relaxed')
                    ui.upload(
                        on_upload=lambda e: handle_parsing(e, stepper),
                        max_file_size=1_000_000, 
                        multiple=False,
                        auto_upload=True
                    ).props('accept=".json" color="indigo-10" flat bordered').classes('w-full mt-4 bg-black/40 rounded-md')
                    with ui.row().classes('justify-center items-center w-full'):
                        ui.button(T("previous_step"), on_click = lambda: stepper.previous(), icon="arrow_upward").classes('mt-4 border border-yellow-500 hover:border-yellow-400 transparent')

                with ui.step("import_json_step3", T("import_json_step_3_title")).classes('text-md text-gray-300 leading-relaxed'):
                    ui.markdown(T("import_json_step_3_desc")).classes('text-lg text-gray-300 leading-relaxed')
                    review_container = ui.column().classes('w-full')
                    # Navigation
                    with ui.row().classes('mt-6 w-full justify-between'):
                        ui.button(T("cancel_or_reupload"), icon="arrow_upward", on_click=stepper.previous).classes('border border-red-500 text-red-400 transparent')
                        ui.button(T("confirm_import"), icon="check_circle", on_click=lambda: finalize_import(stepper)).classes('bg-green-600 text-white hover:bg-green-500')

                # STEP 4: SUCCESS
                with ui.step("import_json_step4", T("import_json_step_4_title")).classes('text-md text-gray-300 leading-relaxed').props("active-color='green'"):
                    ui.label(T("import_json_step_4_desc")).classes('text-lg text-green-400 mb-4')
                    with ui.row():
                        ui.button(T("go_to_bookshelf"), icon="library_books", on_click=lambda: ui.navigate.to('/app/my-bookshelf')).classes('border border-indigo-500 transparent')
                        ui.button(T("import_another"), icon="refresh", on_click=lambda: stepper.previous()).classes('ml-4 border border-white transparent')
            