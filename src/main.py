from nicegui import ui
from fastapi import FastAPI
from src.ui import layout
from src.services.echonet_service import start_echonet_service
from src.services.simulation_service import start_simulation_service

app = FastAPI()

@ui.page('/')
def main_page():
    layout.create_ui()

@app.on_event("startup")
async def startup_event():
    # Start Simulation Loop
    await start_simulation_service()
    
    # Start ECHONET Service (Wi-Fi & Wi-SUN)
    await start_echonet_service()

ui.run_with(app, title='Home Energy Emulator', storage_secret='secret')
