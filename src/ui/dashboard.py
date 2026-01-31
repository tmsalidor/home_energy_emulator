from nicegui import ui
from src.core.engine import engine

def render():
    is_updating_ui = False
    
    with ui.column().classes('w-full items-center'):
        ui.label('HEMS IoT Emulator').classes('text-4xl font-bold my-4')
        
        # Dashboard Card
        with ui.card().classes('w-96'):
            ui.label('System Status').classes('text-xl font-bold mb-2')
            
            # Status Labels
            lbl_grid = ui.label().classes('text-lg')
            lbl_solar = ui.label().classes('text-lg')
            lbl_battery = ui.label().classes('text-lg')

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
