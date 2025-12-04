from nicegui import ui, app
import os
from src.core.locale_manager import T
from src.pages.common import setup_page, create_navbar

@ui.page('/app')
def app_page():
    if not setup_page(restricted=True):
        return
    create_navbar()
    ui.add_css('assets/global.css')
    with ui.column().classes('w-screen min-h-screen gradient-bg text-white p-8 overflow-y-auto'):
        
        with ui.column().classes('w-full items-center text-center max-w-3xl mx-auto mb-10'):
            ui.label(T("get_started_title").format(username=app.storage.user.get("name"))).classes('text-5xl font-extrabold text-indigo-400 mt-12')
            ui.label(T("get_started_subtitle")).classes('text-xl text-gray-400 mt-2')

        # --- Horizontal Separator ---
        ui.separator().classes('w-1/2 mx-auto bg-white/70 mb-10')

        with ui.grid(columns='1').classes('w-full max-w-5xl mx-auto md:grid-cols-2 gap-8'):
            
            with ui.card().classes('bg-black/30 p-3 rounded-xl shadow-2xl border border-indigo-600/50 hover:border-indigo-500 transition-all duration-300').style("padding-bottom: 0px !important;"):
          
                with ui.row().classes('items-center mb-0 pb-0'):
                    ui.image('/assets/images/library.png').classes('w-16 h-16 p-0 mt-6 ml-6 object-cover')
                    ui.label('Step 1').classes('text-sm font-semibold text-gray-500 ml-2')

                with ui.column().classes('p-6'):
                    ui.label(T("step_1_title")).classes('text-3xl font-bold mb-3 text-white')
                    
                    ui.markdown(T("step_1_desc", navigate_to_import_json='/app/import-json', navigate_to_library='/app/public-library')).classes('text-lg text-gray-300 leading-relaxed')
                    
                    ui.element('img').props('src="/assets/images/deck.png"') \
                        .classes('w-full h-48 object-contain opacity-70 rounded-md')

            with ui.card().classes('bg-black/30 p-3 rounded-xl shadow-2xl border border-green-600/50 hover:border-green-500 transition-all duration-300'):
        
                with ui.row().classes('items-center mb-0 pb-0'):
                    ui.image('/assets/images/person_studying.png').classes('w-16 h-16 p-0 mt-6 ml-6 object-cover')
                    ui.label('Step 2').classes('text-sm font-semibold text-gray-500 ml-2')

                with ui.column().classes('p-6'):
                    ui.label(T("step_2_title")).classes('text-3xl font-bold mb-3 text-white')
   
                    ui.markdown(T("step_2_desc", navigate_to_bookshelf='/app/my-bookshelf')).classes('text-lg text-gray-300 leading-relaxed')

                    ui.element('img').props('src="/assets/images/lashing_an_f.png"') \
                        .classes('w-full h-48 object-contain opacity-70 rounded-md')
                
        # --- Final Footer/Call to Action ---
        with ui.column().classes('w-full items-center text-center mt-12'):
            ui.label("Happy Learning!").classes('text-2xl font-semibold text-gray-500')
