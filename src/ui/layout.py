from nicegui import ui
from src.ui import dashboard, settings, inspector

def create_ui():
    with ui.tabs().classes('w-full') as tabs:
        dashboard_tab = ui.tab('Dashboard')
        settings_tab = ui.tab('Settings')
        inspector_tab = ui.tab('Inspector')

    with ui.tab_panels(tabs, value=dashboard_tab).classes('w-full'):
        with ui.tab_panel(dashboard_tab):
            dashboard.render()

        with ui.tab_panel(settings_tab):
            settings.render()

        with ui.tab_panel(inspector_tab):
            inspector.render()
