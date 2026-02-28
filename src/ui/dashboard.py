from nicegui import ui
from src.core.engine import engine
from src.core.version import get_git_info
from src.config.settings import settings

def render():
    is_updating_ui = False
    
    with ui.column().classes('w-full items-center'):
        ui.label('Home Energy Emulator').classes('text-4xl font-bold my-4')
        
        # Dashboard Card
        with ui.card().classes('w-96'):
            ui.label('System Status').classes('text-xl font-bold mb-2')
            
            # Status Labels
            lbl_grid = ui.label().classes('text-lg')
            lbl_solar = ui.label().classes('text-lg')
            lbl_ac = ui.label().classes('text-lg')
            lbl_wh = ui.label().classes('text-lg')
            lbl_battery = ui.label().classes('text-lg')
            lbl_v2h = ui.label().classes('text-lg')
            
            # Application Version
            ui.separator().classes('my-2')
            ui.label(get_git_info()).classes('text-xs text-gray-400 text-center w-full')

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
                 
            # --- Manual Sliders (Grouped by Class) ---
            
            with ui.row().classes('w-full items-start wrap gap-4'):
                
                # 1. Home Load Control
                with ui.card().classes('w-96 p-4'):
                    ui.label('Home Load').classes('text-lg font-bold mb-2')
                    with ui.row().classes('w-full items-center'):
                        ui.label('Power consumption:').classes('whitespace-nowrap font-bold')
                        sl_load = ui.slider(min=0, max=3000, step=10, value=500,
                                            on_change=lambda e: (manual_override(), setattr(engine, 'current_load_w', float(e.value)))
                                           ).classes('flex-grow')
                        ui.label().bind_text_from(sl_load, 'value', backward=lambda v: f"{v:.2f} W").classes('w-20 text-right')

                # 2. Solar Control
                with ui.card().classes('w-96 p-4'):
                    ui.label('Solar').classes('text-lg font-bold mb-2')
                    with ui.row().classes('w-full items-center'):
                        ui.label('Power generation:').classes('whitespace-nowrap font-bold')
                        sl_solar = ui.slider(min=0, max=5000, step=10, value=0,
                                             on_change=lambda e: (manual_override(), setattr(engine.solar, 'instant_generation_power', float(e.value)))
                                            ).classes('flex-grow')
                        ui.label().bind_text_from(sl_solar, 'value', backward=lambda v: f"{v:.2f} W").classes('w-20 text-right')

                # 3. Air Conditioner Control
                with ui.card().classes('w-96 p-4'):
                    ui.label('Air Conditioner').classes('text-lg font-bold mb-2')

                    with ui.row().classes('w-full items-center'):
                        ui.label('Power consumption setting (heating, cooling, auto):').classes('whitespace-nowrap font-bold')
                        sl_ac_power = ui.slider(min=0, max=3000, step=10, value=settings.echonet.ac_power_w,
                                                on_change=lambda e: (manual_override(), setattr(settings.echonet, 'ac_power_w', float(e.value)))
                                               ).classes('flex-grow')
                        ui.label().bind_text_from(sl_ac_power, 'value', backward=lambda v: f"{int(v)} W").classes('w-20 text-right')

                # 4. Water Heater Control
                with ui.card().classes('w-96 p-4'):
                    ui.label('Water Heater').classes('text-lg font-bold mb-2')
                     
                    # Remaining Hot Water
                    with ui.row().classes('w-full items-center mb-2'):
                        ui.label('Remaining hot water amount:').classes('whitespace-nowrap font-bold')
                        def update_wh_amount(e):
                            if is_updating_ui: return
                            manual_override()
                            pct = float(e.value) / 100.0
                            engine.water_heater.remaining_hot_water = engine.water_heater.tank_capacity * pct
                        sl_wh = ui.slider(min=0, max=100, step=0.1, value=50,
                                          on_change=update_wh_amount
                                         ).classes('flex-grow')
                        ui.label().bind_text_from(sl_wh, 'value', backward=lambda v: f"{v:.1f} %").classes('w-20 text-right')
                     
                    # Power Control
                    with ui.row().classes('w-full items-center'):
                        ui.label('Power consumption:').classes('whitespace-nowrap font-bold')
                         
                        def update_wh_power(e):
                            if is_updating_ui: return
                            manual_override()
                            val = float(e.value)
                            wh = engine.water_heater
                            if val > 0:
                                wh.is_heating = True
                                wh.heating_power_w = val
                                wh.auto_setting = 0x42 # Manual Start
                            else:
                                wh.is_heating = False
                                wh.heating_power_w = 0.0
                                wh.auto_setting = 0x43 # Manual Stop

                        sl_wh_power = ui.slider(min=0, max=3000, step=10, value=0, on_change=update_wh_power).classes('flex-grow')
                        ui.label().bind_text_from(sl_wh_power, 'value', backward=lambda v: f"{int(v)} W").classes('w-20 text-right')

                # 5. Battery Control
                with ui.card().classes('w-96 p-4'):
                    ui.label('Battery').classes('text-lg font-bold mb-2')
                    
                    # SOC Control
                    with ui.row().classes('w-full items-center mb-2'):
                        ui.label('SOC:').classes('whitespace-nowrap font-bold')
                        sl_soc = ui.slider(min=0, max=100, step=0.1, value=50, 
                                           on_change=lambda e: (manual_override(), setattr(engine.battery, 'soc', float(e.value)))
                                          ).classes('flex-grow')
                        ui.label().bind_text_from(sl_soc, 'value', backward=lambda v: f"{v:.1f} %").classes('w-20 text-right')

                    # Power Control
                    with ui.row().classes('w-full items-center'):
                        ui.label('Power flow:').classes('whitespace-nowrap font-bold')
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

                # 6. V2H Control
                with ui.card().classes('w-96 p-4'):
                    ui.label('V2H (EV Charger/Discharger)').classes('text-lg font-bold mb-2')

                    # SOC (残容量)
                    with ui.row().classes('w-full items-center mb-2'):
                        ui.label('SOC:').classes('whitespace-nowrap font-bold')
                        def update_v2h_soc(e):
                            if is_updating_ui: return
                            manual_override()
                            v2h = engine.v2h
                            pct = float(e.value) / 100.0  # 0-100% -> 0.0-1.0
                            v2h.remaining_capacity_wh = v2h.battery_capacity_wh * pct
                        sl_v2h_soc = ui.slider(min=0, max=100, step=0.1, value=50,
                                               on_change=update_v2h_soc).classes('flex-grow')
                        ui.label().bind_text_from(sl_v2h_soc, 'value', backward=lambda v: f"{v:.1f} %").classes('w-20 text-right')

                    # 充電電力設定値 (0xEB)
                    with ui.row().classes('w-full items-center mb-2'):
                        ui.label('Charging power setting:').classes('whitespace-nowrap font-bold')
                        sl_v2h_charge = ui.slider(min=0, max=6000, step=10, value=3000,
                                                  on_change=lambda e: (manual_override(), setattr(engine.v2h, 'charge_power_w', float(e.value)))
                                                 ).classes('flex-grow')
                        ui.label().bind_text_from(sl_v2h_charge, 'value', backward=lambda v: f"{int(v)} W").classes('w-20 text-right')

                    # 放電電力設定値 (0xEC)
                    with ui.row().classes('w-full items-center'):
                        ui.label('Max discharging power setting:').classes('whitespace-nowrap font-bold')
                        sl_v2h_discharge = ui.slider(min=0, max=6000, step=10, value=3000,
                                                     on_change=lambda e: (manual_override(), setattr(engine.v2h, 'discharge_power_w', float(e.value)))
                                                    ).classes('flex-grow')
                        ui.label().bind_text_from(sl_v2h_discharge, 'value', backward=lambda v: f"{int(v)} W").classes('w-20 text-right')


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
        
        lbl_battery.set_text(f"Battery: {bat.soc:.1f}% ({state_str})")

        # 2. Update Sliders from Engine State (Scenario or Manual or ECHONET Lite)
        
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

            # Water Heater
            wh = engine.water_heater
            state_wh = "Stopped"
            if wh.is_heating: state_wh = "Heating"
            wh_pct = (wh.remaining_hot_water / wh.tank_capacity * 100.0) if wh.tank_capacity > 0 else 0.0
            lbl_wh.set_text(f"Water Heater: {wh_pct:.1f}% ({state_wh})")
            
            sl_wh.value = (wh.remaining_hot_water / wh.tank_capacity * 100.0) if wh.tank_capacity > 0 else 0
            
            # Water Heater Power
            if wh.is_heating:
                sl_wh_power.value = wh.heating_power_w
            else:
                sl_wh_power.value = 0.0

            # V2H
            v2h = engine.v2h
            v2h_mode_names = {0x42: 'Charging', 0x43: 'Discharging', 0x44: 'Standby', 0x47: 'Stop'}
            v2h_conn = 'Connected' if v2h.vehicle_connected else 'Disconnected'
            v2h_mode = v2h_mode_names.get(v2h.operation_mode, f'0x{v2h.operation_mode:02X}')
            if v2h.battery_capacity_wh > 0:
                v2h_soc_pct = v2h.remaining_capacity_wh / v2h.battery_capacity_wh * 100.0
            else:
                v2h_soc_pct = 0.0
            lbl_v2h.set_text(f"V2H: {v2h_soc_pct:.1f}% ({v2h_conn}, {v2h_mode})")

            # Air Conditioner
            ac = engine.air_conditioner
            ac_mode_names = {0x40: 'Other', 0x41: 'Auto', 0x42: 'Cool', 0x43: 'Heat', 0x44: 'Dehum', 0x45: 'Fan'}
            ac_state = 'ON' if ac.is_running else 'OFF'
            ac_mode = ac_mode_names.get(ac.operation_mode, f'0x{ac.operation_mode:02X}')
            lbl_ac.set_text(f"AC: {ac.instant_power_w:.0f}W ({ac_state}, {ac_mode})")
            sl_ac_power.value = settings.echonet.ac_power_w

            # V2H スライダー更新
            sl_v2h_soc.value = v2h_soc_pct
            sl_v2h_charge.value = v2h.charge_power_w
            sl_v2h_discharge.value = v2h.discharge_power_w
        finally:
            is_updating_ui = False
        
    ui.timer(0.5, update_ui)
