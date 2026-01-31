from nicegui import ui
from fastapi import FastAPI
from src.core.engine import engine
from src.config.settings import settings
import src.core.echonet_consts as ec
import socket
import struct

app = FastAPI()

@ui.page('/')
def main_page():
    # Timer to update simulation logic was moved to background task (startup_event)
    # ui.timer(settings.simulation.update_interval_sec, engine.update_simulation)
    
    # Flag to prevent recursion when updating UI from engine state
    is_updating_ui = False
    
    with ui.tabs().classes('w-full') as tabs:
        dashboard_tab = ui.tab('Dashboard')
        settings_tab = ui.tab('Settings')
        inspector_tab = ui.tab('Inspector')

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

                     # 4. Battery SOC Control
                     with ui.row().classes('w-full items-center mt-2'):
                         ui.label('SOC:').classes('w-20 font-bold')
                         sl_soc = ui.slider(min=0, max=100, step=0.1, value=50, 
                                            on_change=lambda e: (manual_override(), setattr(engine.battery, 'soc', float(e.value)))
                                           ).classes('flex-grow')
                         ui.label().bind_text_from(sl_soc, 'value', backward=lambda v: f"{v:.1f} %").classes('w-20 text-right')


        with ui.tab_panel(settings_tab):
            with ui.column().classes('w-full mx-auto'):
                ui.label('Configuration').classes('text-2xl font-bold mb-4')
                
                # Action Buttons Row (Placed at top)
                actions_row = ui.row().classes('w-full mb-4')
                
                # --- Settings Container (Grid Layout or Flex) ---
                with ui.row().classes('w-full items-start wrap gap-4'):
                    
                    # 1. Wi-SUN Settings Card
                    with ui.card().classes('w-96 p-4'):
                        ui.label('Wi-SUN Settings').classes('text-lg font-bold mb-2')
                        ui.label('Requires Restart').classes('text-xs text-red-500 mb-2')
                        
                        id_input = ui.input('B-Route ID', value=settings.communication.b_route_id, 
                                            placeholder='32 chars hex').classes('w-full')
                        pwd_input = ui.input('B-Route Password', value=settings.communication.b_route_password, 
                                             placeholder='12 chars').classes('w-full')

                    # 2. ECHONET Lite Property Settings
                    with ui.column().classes('flex-1 min-w-[300px] gap-4'):
                        
                        # Common Properties
                        with ui.card().classes('w-full p-4'):
                            ui.label('ECHONET Common').classes('text-lg font-bold mb-2')
                            maker_input = ui.input('Maker Code (0x8A)', value=settings.echonet.maker_code,
                                                   placeholder='e.g. 000000').classes('w-full')
                        
                        # Node Profile
                        with ui.card().classes('w-full p-4'):
                            ui.label('Node Profile (0x0EF001)').classes('text-lg font-bold mb-2')
                            np_id_input = ui.input('Identification Number', value=settings.echonet.node_profile_id,
                                                   placeholder='17 bytes hex').classes('w-full')

                        # Solar
                        with ui.card().classes('w-full p-4'):
                            ui.label('Solar Power (0x027901)').classes('text-lg font-bold mb-2')
                            solar_id_input = ui.input('Identification Number', value=settings.echonet.solar_id,
                                                      placeholder='17 bytes hex').classes('w-full')
                                                      
                        # Battery
                        with ui.card().classes('w-full p-4'):
                            ui.label('Storage Battery (0x027D01)').classes('text-lg font-bold mb-2')
                            bat_id_input = ui.input('Identification Number', value=settings.echonet.battery_id,
                                                    placeholder='17 bytes hex').classes('w-full')
                            bat_cap_input = ui.number('Rated Capacity (Wh)', value=settings.echonet.battery_rated_capacity_wh,
                                                      step=100).classes('w-full')

                        # Smart Meter
                        with ui.card().classes('w-full p-4'):
                            ui.label('Smart Meter (0x028801)').classes('text-lg font-bold mb-2')
                            sm_id_input = ui.input('Identification Number', value=settings.echonet.smart_meter_id,
                                                   placeholder='17 bytes hex').classes('w-full')

                def save_settings():
                    settings.communication.b_route_id = id_input.value
                    settings.communication.b_route_password = pwd_input.value
                    settings.echonet.maker_code = maker_input.value
                    settings.echonet.node_profile_id = np_id_input.value
                    settings.echonet.solar_id = solar_id_input.value
                    settings.echonet.battery_id = bat_id_input.value
                    settings.echonet.battery_rated_capacity_wh = float(bat_cap_input.value or 0)
                    settings.echonet.smart_meter_id = sm_id_input.value
                    
                    settings.save_to_yaml()
                    ui.notify('Settings saved. Please restart the application.', type='positive')
                
                def reset_settings():
                    import os
                    user_path = "config/user_settings.yaml"
                    if os.path.exists(user_path):
                        os.remove(user_path)
                        ui.notify('Settings reset to defaults. Please restart the application.', type='warning')
                    else:
                        ui.notify('Already using default settings.', type='info')

                with actions_row:
                    ui.button('Save Settings', on_click=save_settings).classes('flex-1')
                    ui.button('Reset to Defaults', on_click=reset_settings, color='red').classes('flex-1 ml-4')

        with ui.tab_panel(inspector_tab):
            # Inspector UI
            with ui.column().classes('w-full'):
                ui.label('ECHONET Lite Property Inspector').classes('text-2xl font-bold mb-4')
                
                # Action Buttons Row (Placed at top)
                inspector_actions = ui.row().classes('mb-4')
                
                # Container for inspector content
                inspector_container = ui.column().classes('w-full gap-4')
                
                # State persistence for expansion items
                expansion_states = {}

                def refresh_inspector():
                    inspector_container.clear()
                    
                    # Helper to render controller info
                    def render_controller(name, ctrl):
                        with inspector_container:
                            ui.label(f'Controller: {name}').classes('text-xl font-bold mt-4 text-blue-600')
                            
                            if not hasattr(ctrl, '_objects') or not ctrl._objects:
                                ui.label('No objects registered.').classes('text-gray-500 italic ml-4')
                                return

                            # Iterate over registered objects
                            for key, obj in ctrl._objects.items():
                                # key is (Group, Code, Instance)
                                group, code, inst = key
                                obj_name = f"Class {group:02X}-{code:02X} ({ec.get_class_name(group, code)}) Instance {inst:02X}"
                                
                                # Determine initial state (Default False if not in dict)
                                is_expanded = expansion_states.get(key, False)

                                with ui.card().classes('w-full p-2 bg-gray-50 ml-4'):
                                    # Create expansion with persisted state and update callback
                                    expansion = ui.expansion(obj_name, value=is_expanded).classes('w-full text-lg')
                                    expansion.on_value_change(lambda e, k=key: expansion_states.update({k: e.value}))
                                    
                                    with expansion:
                                        # Property Table
                                        # Columns: EPC, Name, Value(Hex), Value(Raw/Int if logic exists)
                                        # We only show Hex for generic inspector
                                        
                                        # Get supported EPCs
                                        # Assuming Adapter has _get_supported_epcs() (BaseAdapter has it)
                                        # If not, we can't inspect easily without set map
                                        epcs = []
                                        if hasattr(obj, '_get_supported_epcs'):
                                            epcs = obj._get_supported_epcs()
                                        else:
                                            # Fallback: Try common ones or check get_map
                                            epcs = [0x80, 0x82, 0x88, 0x8A] 
                                        
                                        # Prepare Rows
                                        rows = []
                                        for epc in epcs:
                                            # Get Name
                                            name = ec.get_epc_name(group, code, epc)
                                            
                                            # Get Value
                                            try:
                                                val_bytes = obj.get_property(epc)
                                                val_hex = val_bytes.hex().upper() if val_bytes else "None"
                                            except Exception as e:
                                                val_hex = f"Error: {e}"
                                            
                                            rows.append({
                                                'epc': f"0x{epc:02X}",
                                                'name': name,
                                                'value': val_hex
                                            })
                                        
                                        ui.table(
                                            columns=[
                                                {'name': 'epc', 'label': 'EPC', 'field': 'epc', 'align': 'left'},
                                                {'name': 'name', 'label': 'Property Name', 'field': 'name', 'align': 'left'},
                                                {'name': 'value', 'label': 'Current Value (Hex)', 'field': 'value', 'align': 'left'},
                                            ],
                                            rows=rows,
                                            pagination=None
                                        ).classes('w-full')

                    # Render Wi-Fi Controller (Solar/Battery)
                    # Need to import or access global controllers. 
                    # They are defined at module level bottom, so we access via module or import inside function?
                    # Python allows accessing module globals if they exist.
                    # We will import them at top of file or use local import.
                    from src.core.echonet import wifi_echonet_ctrl, wisun_echonet_ctrl
                    render_controller("Wi-Fi (UDP port 3610)", wifi_echonet_ctrl)
                    render_controller("Wi-SUN (B-Route Serial)", wisun_echonet_ctrl)

                with inspector_actions:
                    ui.button('Refresh Properties', on_click=refresh_inspector, icon='refresh')
                
                # Initial Load (Delayed to ensure startup finished)
                ui.timer(1.0, refresh_inspector, once=True)

    # UI Update Loop (Defined after sliders to access them)
    # ... (No change in update_ui logic needed for now) ...
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

        # 2. Update Sliders from Engine State (Scenario or Manual or ECHONET Lite)
        # Always update UI from model unless user is currently interacting (handled by separate mechanism if needed, 
        # but here we rely on is_updating_ui flag to suppress on_change loop)
        
        # Guard: If we are already in a callback (is_updating_ui check at slider event), this timer update might trigger change?
        # No, slider.value = X triggers on_change? Yes.
        # So we set is_updating_ui = True here to block the on_change handler from writing back to engine.
        is_updating_ui = True
        try:
            # Load
            if hasattr(engine, 'current_load_w'):
                 sl_load.value = engine.current_load_w
                 
            # Solar
            sl_solar.value = engine.solar.instant_generation_power
            
            # Battery
            bat = engine.battery
            if bat.is_charging:
                sl_bat.value = bat.instant_charge_power
            elif bat.is_discharging:
                sl_bat.value = -bat.instant_discharge_power
            else:
                sl_bat.value = 0.0
            
            # Battery SOC
            sl_soc.value = bat.soc
        finally:
            is_updating_ui = False
        
    ui.timer(0.5, update_ui)


# --- ECHONET Lite UDP Server Setup ---
import asyncio
import logging
from src.core.echonet import wifi_echonet_ctrl, wisun_echonet_ctrl # Separate controllers
from src.core.adapters import SolarAdapter, BatteryAdapter, NodeProfileAdapter, SmartMeterAdapter # Added SmartMeterAdapter
from src.core.wisun import wisun_manager # Import Wi-SUN Manager

logger = logging.getLogger("uvicorn")

class EchonetProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"ECHONET Lite UDP Server (Wi-Fi) listening on port {settings.communication.echonet_port}")

    def datagram_received(self, data, addr):
        # Dispatch to Wi-Fi controller
        # Note: addr is (ip, port)
        res = wifi_echonet_ctrl.handle_packet(data, addr)
        if res:
            self.transport.sendto(res, addr)

async def simulation_loop():
    logger.info("Starting Background Simulation Loop")
    while True:
        try:
            engine.update_simulation()
        except Exception as e:
            logger.error(f"Error in simulation loop: {e}")
        
        await asyncio.sleep(settings.simulation.update_interval_sec)

@app.on_event("startup")
async def startup_event():
    # --- 1. Wi-Fi Controller Setup (Solar + Battery) ---
    # Node Profile for Wi-Fi: Solar(0279) and Battery(027D)
    wifi_instances = [(0x02, 0x79, 0x01), (0x02, 0x7D, 0x01)]
    wifi_echonet_ctrl.register_instance(0x0E, 0xF0, 0x01, NodeProfileAdapter(wifi_instances))
    
    wifi_echonet_ctrl.register_instance(0x02, 0x79, 0x01, SolarAdapter(engine.solar))
    wifi_echonet_ctrl.register_instance(0x02, 0x7D, 0x01, BatteryAdapter(engine.battery))
    
    # --- 2. Wi-SUN Controller Setup (Smart Meter) ---
    # Node Profile for Wi-SUN: Smart Meter(0288)
    wisun_instances = [(0x02, 0x88, 0x01)]
    wisun_echonet_ctrl.register_instance(0x0E, 0xF0, 0x01, NodeProfileAdapter(wisun_instances))
    
    # Smart Meter: Class Group 0x02, Class Code 0x88, Instance 0x01
    wisun_echonet_ctrl.register_instance(0x02, 0x88, 0x01, SmartMeterAdapter(engine.smart_meter))

    
    # --- 3. Start UDP Server (Wi-Fi) with Multicast Support ---
    try:
        loop = asyncio.get_running_loop()
        
        # Create Socket manually for Multicast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to all interfaces
        sock.bind(('0.0.0.0', settings.communication.echonet_port))
        
        # Join Multicast Group 224.0.23.0
        mreq = struct.pack("4sl", socket.inet_aton("224.0.23.0"), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Set Multicast TTL
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        
        await loop.create_datagram_endpoint(
            lambda: EchonetProtocol(),
            sock=sock
        )
        logger.info("ECHONET Lite UDP Server started with Multicast (224.0.23.0) support.")

        # --- 3.5 Send Instance List Notification (INF) ---
        # Announce presence to the network via Multicast
        try:
            # 1. Get Instance List (D5) from Node Profile
            # Node Profile instance tuple: (0x0E, 0xF0, 0x01)
            node_profile = wifi_echonet_ctrl._objects.get((0x0E, 0xF0, 0x01))
            if node_profile:
                d5_value = node_profile.get_property(0xD5) # Instance List Notification
                if d5_value:
                    # 2. Build ECHONET Lite Frame (Format 1)
                    # EHD(2) + TID(2) + SEOJ(3) + DEOJ(3) + ESV(1) + OPC(1) + EPC(1) + PDC(1) + EDT(N)
                    tid = b'\x00\x00' # Transaction ID
                    seoj = b'\x0E\xF0\x01' # Source: Node Profile
                    deoj = b'\x0E\xF0\x01' # Dest: Node Profile (Broadcast to all nodes)
                    esv = b'\x73' # INF (Property Value Notification)
                    opc = b'\x01'
                    epc = b'\xD5'
                    pdc = bytes([len(d5_value)])
                    edt = d5_value
                    
                    frame = b'\x10\x81' + tid + seoj + deoj + esv + opc + epc + pdc + edt
                    
                    # 3. Send to Multicast
                    sock.sendto(frame, ('224.0.23.0', 3610))
                    logger.info("Sent Initial Instance List Notification (INF) to 224.0.23.0:3610")
        except Exception as e:
            logger.error(f"Failed to send initial announcement: {e}")
            
    except Exception as e:
        logger.error(f"Failed to start UDP server: {e}")

    # 4. Start Wi-SUN Manager (B-Route)
    # Don't block startup if dongle is missing (fail-fast called for system? or just log error)
    # Requirements said "Fail-fast" but maybe for the whole app? 
    # For now, let's just start it without awaiting fully if it has internal loop,
    # But wisun.start() calls serial connect which might fail.
    # We use create_task to run it in background or await if initialization is critical?
    # Requirement: "Error stop (Fail-fast)". So we should await and let it crash if fails?
    # But simulation UI is also important. Let's log heavily.
    asyncio.create_task(wisun_manager.start())

    # 5. Start Background Simulation Loop
    asyncio.create_task(simulation_loop())

ui.run_with(app, title='HEMS Emulator', storage_secret='secret')
