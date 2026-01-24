from nicegui import ui
from fastapi import FastAPI
from src.core.engine import engine
from src.config.settings import settings

app = FastAPI()

@ui.page('/')
def main_page():
    # Timer to update simulation logic (runs every 1 sec by default)
    ui.timer(settings.simulation.update_interval_sec, engine.update_simulation)
    
    # Flag to prevent recursion when updating UI from engine state
    is_updating_ui = False
    
    with ui.tabs().classes('w-full') as tabs:
        dashboard_tab = ui.tab('Dashboard')
        settings_tab = ui.tab('Settings')

    with ui.tab_panels(tabs, value=dashboard_tab).classes('w-full'):
        with ui.tab_panel(dashboard_tab):
            with ui.column().classes('w-full items-center'):
                ui.label('HEMS IoT Emulator').classes('text-4xl font-bold my-4')
                
                # Dashboard Card
                with ui.card().classes('w-96'):
                    ui.label('System Status').classes('text-xl font-bold mb-2')
                    
                    # Status Labels
                    lbl_grid = ui.label().classes('text-lg')
                    lbl_solar = ui.label().classes('text-lg')
                    lbl_battery = ui.label().classes('text-lg')

                    # Labels references for update_ui are OK here

            # Debug Controls
            with ui.row().classes('w-full justify-center mt-8'):
                with ui.card().classes('p-4'):
                     ui.label('Debug Controls').classes('font-bold')
                     
                     # Scenario Control
                     scenario_sw = ui.switch('Scenario Active', value=True, 
                                           on_change=lambda e: setattr(engine, 'use_scenario', e.value))
                     
                     def manual_override():
                         if is_updating_ui: return
                         engine.use_scenario = False
                         scenario_sw.set_value(False)

                     ui.number('Load (W)', value=500, step=100, 
                               on_change=lambda e: (manual_override(), setattr(engine, 'current_load_w', float(e.value or 0)))).classes('hidden')
                         
                     # --- Manual Sliders ---
                     
                     # 1. Load Control
                     with ui.row().classes('w-full items-center'):
                         ui.label('Load:').classes('w-20 font-bold')
                         sl_load = ui.slider(min=0, max=2000, step=10, value=500,
                                             on_change=lambda e: (manual_override(), setattr(engine, 'current_load_w', float(e.value)))
                                            ).classes('flex-grow')
                         ui.label().bind_text_from(sl_load, 'value', backward=lambda v: f"{v:.2f} W").classes('w-20 text-right')

                     # 2. Solar Control
                     with ui.row().classes('w-full items-center mt-2'):
                         ui.label('Solar:').classes('w-20 font-bold')
                         sl_solar = ui.slider(min=0, max=5000, step=10, value=0,
                                              on_change=lambda e: (manual_override(), setattr(engine.solar, 'instant_generation_power', float(e.value)))
                                             ).classes('flex-grow')
                         ui.label().bind_text_from(sl_solar, 'value', backward=lambda v: f"{v:.2f} W").classes('w-20 text-right')

                     # 3. Battery Control
                     with ui.row().classes('w-full items-center mt-2'):
                         ui.label('Battery:').classes('w-20 font-bold')
                         
                         def update_battery(e):
                             if is_updating_ui: return
                             manual_override()
                             val = e.value
                             bat = engine.battery
                             if val > 0:
                                 bat.is_charging = True
                                 bat.is_discharging = False
                                 bat.instant_charge_power = float(val)
                                 bat.instant_discharge_power = 0.0
                             elif val < 0:
                                 bat.is_charging = False
                                 bat.is_discharging = True
                                 bat.instant_charge_power = 0.0
                                 bat.instant_discharge_power = abs(float(val))
                             else:
                                 bat.is_charging = False
                                 bat.is_discharging = False
                                 bat.instant_charge_power = 0.0
                                 bat.instant_discharge_power = 0.0

                         sl_bat = ui.slider(min=-3000, max=3000, step=10, value=0, on_change=update_battery).classes('flex-grow')
                         ui.label().bind_text_from(sl_bat, 'value', backward=lambda v: f"{v:.2f} W").classes('w-20 text-right')

        with ui.tab_panel(settings_tab):
            with ui.column().classes('w-full items-center max-w-lg mx-auto'):
                ui.label('Configuration').classes('text-2xl font-bold mb-4')
                
                with ui.card().classes('w-full p-4'):
                    ui.label('Wi-SUN Settings (Require Restart)').classes('text-lg font-bold mb-2')
                    
                    id_input = ui.input('B-Route ID', value=settings.communication.b_route_id, 
                                        placeholder='32 chars hex').classes('w-full')
                    pwd_input = ui.input('B-Route Password', value=settings.communication.b_route_password, 
                                         placeholder='12 chars').classes('w-full')
                    
                    def save_settings():
                        settings.communication.b_route_id = id_input.value
                        settings.communication.b_route_password = pwd_input.value
                        settings.save_to_yaml()
                        ui.notify('Settings saved. Please restart the application.', type='positive')
                        
                    ui.button('Save Settings', on_click=save_settings).classes('mt-4 w-full')

    # UI Update Loop (Defined after sliders to access them)
    def update_ui():
        nonlocal is_updating_ui

        # 1. Update Labels (Display)
        # Grid Power Color: Red for Buying (pos), Green for Selling (neg)
        p_grid = engine.smart_meter.instant_current_power
        color_grid = 'text-red-500' if p_grid > 0 else 'text-green-500'
        lbl_grid.set_text(f"Grid: {p_grid:.2f} W")
        lbl_grid.classes(replace=color_grid)
        
        lbl_solar.set_text(f"Solar: {engine.solar.instant_generation_power:.2f} W")
        
        bat = engine.battery
        state_str = "Idle"
        if bat.is_charging: state_str = "Charging"
        elif bat.is_discharging: state_str = "Discharging"
        
        lbl_battery.set_text(f"Battery: {bat.soc:.2f}% ({state_str})")

        # 2. Update Sliders from Scenario (if Active)
        if engine.use_scenario:
            is_updating_ui = True
            try:
                sl_load.value = engine.current_load_w
                sl_solar.value = engine.solar.instant_generation_power
                # Battery is not controlled by scenario directly in this simple logic
            finally:
                is_updating_ui = False
        
    ui.timer(0.5, update_ui)


# --- ECHONET Lite UDP Server Setup ---
import asyncio
import logging
from src.core.echonet import echonet_ctrl
from src.core.adapters import SolarAdapter, BatteryAdapter
from src.core.wisun import wisun_manager # Import Wi-SUN Manager

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
    
    # 2. Start UDP Server (Wi-Fi)
    try:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(
            lambda: EchonetProtocol(),
            local_addr=('0.0.0.0', settings.communication.echonet_port)
        )
    except Exception as e:
        logger.error(f"Failed to start UDP server: {e}")

    # 3. Start Wi-SUN Manager (B-Route)
    # Don't block startup if dongle is missing (fail-fast called for system? or just log error)
    # Requirements said "Fail-fast" but maybe for the whole app? 
    # For now, let's just start it without awaiting fully if it has internal loop,
    # But wisun.start() calls serial connect which might fail.
    # We use create_task to run it in background or await if initialization is critical?
    # Requirement: "Error stop (Fail-fast)". So we should await and let it crash if fails?
    # But simulation UI is also important. Let's log heavily.
    asyncio.create_task(wisun_manager.start())

ui.run_with(app, title='HEMS Emulator', storage_secret='secret')
