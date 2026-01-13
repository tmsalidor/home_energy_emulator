from nicegui import ui
from fastapi import FastAPI
from src.core.engine import engine
from src.config.settings import settings

app = FastAPI()

@ui.page('/')
def main_page():
    # Timer to update simulation logic (runs every 1 sec by default)
    ui.timer(settings.simulation.update_interval_sec, engine.update_simulation)
    
    with ui.column().classes('w-full items-center'):
        ui.label('HEMS IoT Emulator').classes('text-4xl font-bold my-4')
        
        # Dashboard Card
        with ui.card().classes('w-96'):
            ui.label('System Status').classes('text-xl font-bold mb-2')
            
            # Status Labels
            lbl_grid = ui.label().classes('text-lg')
            lbl_solar = ui.label().classes('text-lg')
            lbl_battery = ui.label().classes('text-lg')
            
            # UI Update Loop
            def update_ui():
                # Grid Power Color: Red for Buying (pos), Green for Selling (neg)
                p_grid = engine.smart_meter.instant_current_power
                color_grid = 'text-red-500' if p_grid > 0 else 'text-green-500'
                lbl_grid.set_text(f"Grid: {p_grid:.1f} W").classes(replace=color_grid)
                
                lbl_solar.set_text(f"Solar: {engine.solar.instant_generation_power:.1f} W")
                
                bat = engine.battery
                state_str = "Idle"
                if bat.is_charging: state_str = "Charging"
                elif bat.is_discharging: state_str = "Discharging"
                
                lbl_battery.set_text(f"Battery: {bat.soc:.1f}% ({state_str})")
                
            ui.timer(0.5, update_ui)

    # Debug Controls
    with ui.row().classes('w-full justify-center mt-8'):
        with ui.card().classes('p-4'):
             ui.label('Debug Controls').classes('font-bold')
             
             ui.number('Load (W)', value=500, step=100, 
                       on_change=lambda e: setattr(engine, 'current_load_w', float(e.value or 0)))
             
             with ui.row().classes('items-center'):
                ui.label('Solar Power:')
                ui.switch('Zero/3kW', on_change=lambda e: setattr(engine.solar, 'instant_generation_power', 3000.0 if e.value else 0.0))
             
             with ui.row().classes('items-center'):
                 ui.label('Battery Force:')
                 def toggle_charge(e):
                     engine.battery.is_charging = e.value
                     engine.battery.instant_charge_power = 1000.0 if e.value else 0.0
                 ui.switch('Charge 1kW', on_change=toggle_charge)

# --- ECHONET Lite UDP Server Setup ---
import asyncio
import logging
from src.core.echonet import echonet_ctrl
from src.core.adapters import SolarAdapter, BatteryAdapter

logger = logging.getLogger("uvicorn")

class EchonetProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"ECHONET Lite UDP Server listening on port {settings.communication.echonet_port}")

    def datagram_received(self, data, addr):
        # Dispatch to controller
        # Note: addr is (ip, port)
        res = echonet_ctrl.handle_packet(data, addr)
        if res:
            self.transport.sendto(res, addr)

@app.on_event("startup")
async def startup_event():
    # 1. Register Objects
    # Solar: Class Group 0x02, Class Code 0x79, Instance 0x01
    echonet_ctrl.register_instance(0x02, 0x79, 0x01, SolarAdapter(engine.solar))
    # Battery: Class Group 0x02, Class Code 0x7D, Instance 0x01
    echonet_ctrl.register_instance(0x02, 0x7D, 0x01, BatteryAdapter(engine.battery))
    
    # 2. Start UDP Server
    try:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(
            lambda: EchonetProtocol(),
            local_addr=('0.0.0.0', settings.communication.echonet_port)
        )
    except Exception as e:
        logger.error(f"Failed to start UDP server: {e}")

ui.run_with(app, title='HEMS Emulator', storage_secret='secret')
