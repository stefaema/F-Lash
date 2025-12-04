from typing import List, Optional, Dict
from nicegui import ui, app, events
from sqlmodel import select

from src.pages.common import setup_page, create_navbar
from src.core.locale_manager import T
from src.core.log_manager import logger
from src.database import create_session
from src.models import ActiveDeck, Tag, CardTagLink, Card

from src.services.study_service import (
    initialize_session, 
    get_next_batch, 
    update_session_state, 
    finalize_session,
)
from src.services.deck_service import get_study_metadata

class StudyPageState:
    def __init__(self):
        self.current_card: Optional[Card] = None
        self.is_revealed: bool = False
        self.combo: int = 0
        self.total_cards: int = 0
        self.cards_done: int = 0
        self.active_deck_title: str = "Loading..."
        self.available_tags: Dict[int, str] = {}

@ui.page('/app/study')
def study_page(deck_id: int = None):
    # 1. Security & Setup
    if not setup_page(restricted=True, remove_url_params=True):
        return
    
    if not deck_id:
        logger.warning("Study page accessed without deck_id parameter.")
        ui.navigate.to('/app/my-bookshelf')
        return

    create_navbar()
    ui.add_css('assets/global.css')
    
    # --- STATE & INITIALIZATION ---
    state = StudyPageState()
    local_buffer: List[Card] = []

    # 2. Fetch Deck Metadata
    try:
        user_id = app.storage.user.get('id')
        metadata = get_study_metadata(user_id, deck_id)

        if not metadata:
            logger.warning(f"Unauthorized access attempt to Deck {deck_id} by User {user_id}")
            ui.notify(T("access_denied"), type='negative')
            ui.navigate.to('/app/my-bookshelf')
            return

        state.active_deck_title = metadata["title"]
        state.available_tags = metadata["tags"]
            
    except Exception as e:
        logger.error(f"Error loading study page metadata: {e}")
        ui.notify("System Error: Could not load deck details.", type='negative')
        ui.navigate.to('/app/my-bookshelf')
        return

    # --- UI REFERENCES (Placeholders) ---
    # These will be bound during layout creation, but declared here for scope clarity
    front_content = None
    back_content = None
    hud_container = None
    back_container = None
    controls_container = None
    reveal_btn = None
    progress_label = None
    progress_bar = None
    combo_label = None
    final_score_label = None
    stepper = None

    DIFFICULTY_MAP = {
        1: ('spa', 'text-blue-400'),            # Easiest
        2: ('eco', 'text-green-400'),           # Easy
        3: ('bolt', 'text-yellow-400'),         # Medium
        4: ('warning', 'text-orange-500'),      # Hard
        5: ('local_fire_department', 'text-red-600') # Hardest
    }

    # --- LOGIC CONTROLLERS ---

    def render_hud(card: Card):
        """Updates the Header icons based on the current card."""
        if not hud_container: return
        
        hud_container.clear()
        with hud_container:
            # Left: Tags
            with ui.icon('local_offer', size='sm').classes('text-gray-500 opacity-50 hover:opacity-100 cursor-help transition-opacity'):
                ui.tooltip("Tags hidden for focus").classes('bg-black text-xs')

            # Center: State Emoji
            ui.label('🤔').classes('text-3xl animate-pulse cursor-default select-none hud-emoji')

            # Right: Difficulty
            diff = card.base_difficulty or 3
 
            icon_name, color_class = DIFFICULTY_MAP.get(diff, ('bolt', 'text-gray-500'))
            ui.icon(icon_name, size='sm').classes(f'{color_class} opacity-80')

    def fill_buffer():
        try:
            more_cards = get_next_batch(batch_size=5)
            if more_cards:
                local_buffer.extend(more_cards)
                logger.info(f"Buffer refilled. +{len(more_cards)} cards.")
        except Exception as e:
            logger.error(f"Failed to fetch batch: {e}")
            ui.notify("Network error: Could not fetch cards.", type='negative')

    def finish_run():
        try:
            finalize_session()
        except Exception as e:
            logger.error(f"Error finalizing session: {e}")
            
        if stepper: stepper.next()
        if final_score_label: 
            final_score_label.set_text(T("session_complete_msg").format(count=state.cards_done))

    def load_next_card():
        if not local_buffer:
            fill_buffer()
        
        if not local_buffer:
            logger.info("Buffer empty. Finishing run.")
            finish_run()
            return

        card = local_buffer.pop(0)
        state.current_card = card
        state.is_revealed = False
        
        # Update UI Content
        if front_content: front_content.set_content(card.front_content)
        if back_content: back_content.set_content(card.back_content)

        render_hud(card)
        
        # Reset View State
        if back_container: back_container.set_visibility(False)
        if controls_container: controls_container.set_visibility(False)
        if reveal_btn: 
            reveal_btn.set_visibility(True)
            reveal_btn.enable()
        
        # Update Progress
        progress_val = 0.0
        if state.total_cards > 0:
            progress_val = min(state.cards_done / state.total_cards, 1.0)
            
        if progress_label: progress_label.set_text(f"{state.cards_done} / {state.total_cards}")
        if progress_bar: progress_bar.set_value(progress_val)
        
        if len(local_buffer) < 3:
            fill_buffer()

    def reveal():
        if state.is_revealed: return
        state.is_revealed = True
        
        if reveal_btn: reveal_btn.set_visibility(False)
        if back_container: back_container.set_visibility(True)
        if controls_container: controls_container.set_visibility(True)

        # Update Emoji
        if hud_container and len(list(hud_container)) > 1:
            emoji_lbl = list(hud_container)[1]
            emoji_lbl.set_text('🤓')
            emoji_lbl.classes(add='animate-bounce', remove='animate-pulse')
            emoji_lbl.update()

    def submit_answer(result: str):
        """
        result: 'KNOW' | 'MISS' | 'DISCARD'
        """
        if not state.current_card: 
            logger.warning("Attempted to submit answer with no current card.")
            return
        
        try:
            update_session_state(state.current_card.id, result)
        except Exception as e:
            logger.error(f"Failed to update session state: {e}")
        
        # Update Local State
        if result == 'KNOW':
            state.combo += 1
            state.cards_done += 1
            if combo_label: combo_label.classes('text-yellow-400 scale-125', remove='text-gray-500 scale-100')
        elif result == 'MISS':
            state.combo = 0
            if combo_label: combo_label.classes('text-gray-500 scale-100', remove='text-yellow-400 scale-125')
        elif result == 'DISCARD':
            state.cards_done += 1
        
        if combo_label: combo_label.set_text(f"x{state.combo} COMBO")
        
        load_next_card()

    async def start_run():
        # Parse Inputs
        diff_range = (int(diff_slider.value['min']), int(diff_slider.value['max']))
        
        selected_tags = []
        if tag_select.value:
            selected_tags = [t_id for t_id, name in state.available_tags.items() if name in tag_select.value]

        do_shuffle = shuffle_toggle.value
        
        try:
            total_count = initialize_session(
                active_deck_id=deck_id,
                difficulty_range=diff_range,
                tag_ids=selected_tags if selected_tags else None,
                shuffle=do_shuffle
            )
            state.total_cards = total_count
            state.cards_done = 0
            state.combo = 0
            
            fill_buffer()
            
            if not local_buffer:
                ui.notify(T("no_cards_found_filter"), type='warning')
                return

            load_next_card()
            if stepper: stepper.next()
            
        except Exception as e:
            logger.error(f"Session Start Failed: {e}")
            ui.notify(f"Could not start session: {str(e)}", type='negative')

    # --- KEYBOARD ---
    def handle_key(e: events.KeyEventArguments):
        if not stepper or stepper.value != 'step_arena': return
        if not e.action.keydown: return
        
        if not state.is_revealed:
            if e.key == ' ': reveal()
        else:
            if e.key == '1' or e.key == 'ArrowLeft': submit_answer('MISS')
            elif e.key == '2' or e.key == 'ArrowRight': submit_answer('KNOW')
            elif e.key == 'ArrowDown': submit_answer('DISCARD')

    keyboard = ui.keyboard(on_key=handle_key)

    # --- LAYOUT ---
    with ui.column().classes('w-screen min-h-screen gradient-bg text-white items-center p-4'):
        
        ui.label(T("study_session_title", deck_title=state.active_deck_title))\
            .classes('text-gray-400 text-sm font-bold tracking-widest uppercase mb-2')
        ui.label(state.active_deck_title)\
            .classes('text-3xl font-extrabold text-indigo-300 mb-8 text-center')

        with ui.stepper().props('flat vertical animated')\
            .classes('w-full sm:max-w-4xl bg-black/30 border-y sm:border border-white/10 sm:rounded-xl shadow-2xl p-0 sm:p-6') as stepper:
            
            # --- STEP 1: CONFIG ---
            with ui.step(name='step_config', title=T("setup_session")).props("active-icon='filter_alt' done-icon='check_circle' done-color='green'"):
                
                with ui.column().classes('w-full gap-6'):
                    ui.label(T("filter_difficulty")).classes('font-bold text-gray-300 text-lg mt-2')

                    diff_slider = ui.range(min=1, max=5, value={'min': 1, 'max': 5}).classes("px-2")\
                        .props('snap markers color="indigo-400" track-size="6px" thumb-size="20px"')

                    with ui.row().classes('w-full justify-between px-1'): # Difficulty Legend
                        for level in sorted(DIFFICULTY_MAP.keys()):
                            icon, color = DIFFICULTY_MAP[level]
                            # Render icon centered below the tick
                            with ui.column().classes('items-center gap-0'):
                                ui.icon(icon).classes(f'{color} text-2xl filter drop-shadow-lg')
                    
                    ui.label(T("filter_tags")).classes('font-bold text-gray-300 text-lg mt-4')
                    tag_names = list(state.available_tags.values())
                    
                    if tag_names:
                        tag_select = ui.select(options=tag_names, multiple=True, label="Tags").classes('w-full')
                        tag_select.value = [] 
                        tag_select.props('use-chips map-options outlined dark')
                    else:
                        ui.label(T("no_tags_available")).classes('text-sm italic text-gray-500')
                        tag_select = ui.select(options=[], multiple=True).classes('hidden')
                        tag_select.value = []

                    shuffle_toggle = ui.switch(T("shuffle_deck"), value=True).props('color="green"')

                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button(T("start_studying"), on_click=start_run, icon='play_arrow')\
                            .classes('bg-indigo-600 hover:bg-indigo-500 text-white font-bold')

            # --- STEP 2: ARENA ---
            with ui.step(name='step_arena', title=T("focus_mode")).props("active-icon='quiz'"):
                
                # HUD
                with ui.row().classes('w-full justify-between items-center mb-4 px-4 sm:px-0'):
                    with ui.column().classes('w-1/2'):
                        progress_label = ui.label("0 / 0").classes('text-xs text-gray-400 font-mono')
                        progress_bar = ui.linear_progress(value=0, show_value=False)\
                            .props('size="10px" color="indigo-400" track-color="grey-8" rounded')
                    
                    combo_label = ui.label("x0 COMBO").classes('text-xl font-black italic text-gray-500')

                # Card
                with ui.card().classes('w-full min-h-[400px] bg-gray-900 border border-white/20 flex flex-col items-center justify-center p-8 relative overflow-hidden'):
                    hud_container = ui.row().classes('w-full justify-between items-center absolute top-0 left-0 p-4 z-10')
                    
                    front_content = ui.markdown("Loading...").classes('text-xl text-center text-white mt-8')
                    sep = ui.separator().classes('w-1/2 my-6 opacity-30')

                    with ui.column().classes('w-full items-center fade-in') as back_container:
                        back_content = ui.markdown("").classes('text-lg text-center text-gray-300')
                        back_container.set_visibility(False)
                    
                    sep.bind_visibility_from(back_container)

                # Controls
                with ui.column().classes('w-full items-center mt-6 h-20'):
                    reveal_btn = ui.button("REVEAL (Space)", on_click=reveal)\
                        .props('size=lg color=indigo-600')\
                        .classes('w-full max-w-sm font-bold tracking-widest shadow-lg')
                    
                    with ui.row().classes('gap-4 w-full justify-center') as controls_container:
                        controls_container.set_visibility(False)
                        
                        ui.button(icon='delete', on_click=lambda: submit_answer('DISCARD')) \
                            .props('round flat color=grey size=lg').classes('border border-gray-500 hover:scale-110 transition-transform shadow-gray-900/50 shadow-lg') 
    
                        ui.button(icon='close', on_click=lambda: submit_answer('MISS')) \
                            .props('round color=red-900 size=lg').classes('border border-red-500 hover:scale-110 transition-transform shadow-red-900/50 shadow-lg') 

                        ui.button(icon='check', on_click=lambda: submit_answer('KNOW')) \
                            .props('round color=green-900 size=lg').classes('border border-green-500 hover:scale-110 transition-transform shadow-green-900/50 shadow-lg') 

                ui.button(icon='close', on_click=lambda: ui.navigate.to('/app/my-bookshelf')) \
                    .props('flat round color=grey').classes('absolute top-4 right-4 z-50')

            # --- STEP 3: RESULTS ---
            with ui.step(name='step_results', title=T("results")):
                with ui.column().classes('w-full items-center text-center gap-6 py-10'):
                    ui.icon('emoji_events', size='6rem').classes('text-yellow-400 animate-bounce')
                    ui.label(T("knowledge_acquired")).classes('text-4xl font-black text-white')
                    final_score_label = ui.label("").classes('text-xl text-gray-300')
                    
                    ui.button(T("return2bookshelf"), on_click=lambda: ui.navigate.to('/app/my-bookshelf')) \
                        .classes('bg-indigo-600 text-white px-8 py-2 text-lg font-bold shadow-lg hover:scale-105 transition-transform')
