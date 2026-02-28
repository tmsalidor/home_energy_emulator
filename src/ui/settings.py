from nicegui import ui
from src.config.settings import settings
import os

def render():
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

            # 1.5 Wi-Fi Settings Card (New)
            with ui.card().classes('w-96 p-4'):
                ui.label('Wi-Fi Settings').classes('text-lg font-bold mb-2')
                ui.label('Requires Restart').classes('text-xs text-red-500 mb-2')
                # Checkboxes for devices
                wifi_devs = settings.echonet.wifi_devices

                # Node Profile is always mandatory
                ui.checkbox('Node Profile (0x0EF0)', value=True).props('disable').classes('w-full')

                chk_sm = ui.checkbox('Smart Meter (0x0288)', value='smart_meter' in wifi_devs).classes('w-full')
                chk_solar = ui.checkbox('Solar Power (0x0279)', value='solar' in wifi_devs).classes('w-full')
                chk_battery = ui.checkbox('Storage Battery (0x027D)', value='battery' in wifi_devs).classes('w-full')
                chk_wh = ui.checkbox('Elec. Water Heater (0x026B)', value='water_heater' in wifi_devs).classes('w-full')
                chk_v2h = ui.checkbox('EV Charger/Discharger V2H (0x027E)', value='v2h' in wifi_devs).classes('w-full')
                chk_ac = ui.checkbox('Air Conditioner (0x0130)', value='air_conditioner' in wifi_devs).classes('w-full')

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
                    np_id_input = ui.input('Identification Number (0x83)', value=settings.echonet.node_profile_id,
                                           placeholder='17 bytes hex').classes('w-full')

                # Smart Meter
                with ui.card().classes('w-full p-4'):
                    ui.label('Smart Meter (0x028801)').classes('text-lg font-bold mb-2')
                    sm_id_input = ui.input('Identification Number (0x83)', value=settings.echonet.smart_meter_id,
                                           placeholder='17 bytes hex').classes('w-full')

                # Solar
                with ui.card().classes('w-full p-4'):
                    ui.label('Solar Power (0x027901)').classes('text-lg font-bold mb-2')
                    solar_id_input = ui.input('Identification Number (0x83)', value=settings.echonet.solar_id,
                                              placeholder='17 bytes hex').classes('w-full')
                                              
                # Battery
                with ui.card().classes('w-full p-4'):
                    ui.label('Storage Battery (0x027D01)').classes('text-lg font-bold mb-2')
                    bat_id_input = ui.input('Identification Number (0x83)', value=settings.echonet.battery_id,
                                            placeholder='17 bytes hex').classes('w-full')
                    bat_cap_input = ui.number('Rated Capacity (0xD0) [Wh]', value=settings.echonet.battery_rated_capacity_wh,
                                              step=100).classes('w-full')
                    bat_charge_input = ui.number('Charge Power Limit [W]', value=settings.echonet.battery_charge_power_w,
                                                 step=100).classes('w-full')
                    bat_discharge_input = ui.number('Discharge Power Limit [W]', value=settings.echonet.battery_discharge_power_w,
                                                    step=100).classes('w-full')

                # Water Heater
                with ui.card().classes('w-full p-4'):
                    ui.label('Elec. Water Heater (0x026B01)').classes('text-lg font-bold mb-2')
                    wh_id_input = ui.input('Identification Number (0x83)', value=settings.echonet.water_heater_id,
                                           placeholder='17 bytes hex').classes('w-full')
                    wh_cap_input = ui.number('Tank Capacity (0xE2) [L]', value=settings.echonet.water_heater_tank_capacity,
                                             step=10).classes('w-full')
                    wh_power_input = ui.number('Heating Power [W]', value=settings.echonet.water_heater_power_w,
                                               step=100).classes('w-full')

                # V2H
                with ui.card().classes('w-full p-4'):
                    ui.label('EV Charger/Discharger V2H (0x027E01)').classes('text-lg font-bold mb-2')
                    v2h_id_input = ui.input('Identification Number (0x83)', value=settings.echonet.v2h_id,
                                            placeholder='17 bytes hex').classes('w-full')
                    v2h_cap_input = ui.number('Battery Capacity (0xC0) [Wh]',
                                             value=settings.echonet.v2h_battery_capacity_wh,
                                             step=1000).classes('w-full')
                    v2h_charge_input = ui.number('Charge Power (0xEB) [W]',
                                                 value=settings.echonet.v2h_charge_power_w,
                                                 step=100).classes('w-full')
                    v2h_discharge_input = ui.number('Discharge Power (0xEC) [W]',
                                                    value=settings.echonet.v2h_discharge_power_w,
                                                    step=100).classes('w-full')

                # Air Conditioner
                with ui.card().classes('w-full p-4'):
                    ui.label('Air Conditioner (0x013001)').classes('text-lg font-bold mb-2')
                    ac_id_input = ui.input('Identification Number (0x83)', value=settings.echonet.ac_id,
                                           placeholder='17 bytes hex').classes('w-full')
                    ac_power_input = ui.number('Power Auto/Cool/Heat/Dehum (0x84) [W]',
                                               value=settings.echonet.ac_power_w,
                                               step=10).classes('w-full')

        def save_settings():
            settings.communication.b_route_id = id_input.value
            settings.communication.b_route_password = pwd_input.value
            
            # Save Wi-Fi Devices
            new_wifi_devs = []
            if chk_sm.value: new_wifi_devs.append('smart_meter')
            if chk_solar.value: new_wifi_devs.append('solar')
            if chk_battery.value: new_wifi_devs.append('battery')
            if chk_wh.value: new_wifi_devs.append('water_heater')
            if chk_v2h.value: new_wifi_devs.append('v2h')
            if chk_ac.value: new_wifi_devs.append('air_conditioner')
            settings.echonet.wifi_devices = new_wifi_devs
            
            settings.echonet.maker_code = maker_input.value
            settings.echonet.node_profile_id = np_id_input.value
            settings.echonet.solar_id = solar_id_input.value
            settings.echonet.battery_id = bat_id_input.value
            settings.echonet.battery_rated_capacity_wh = float(bat_cap_input.value or 0)
            settings.echonet.battery_charge_power_w = float(bat_charge_input.value or 0)
            settings.echonet.battery_discharge_power_w = float(bat_discharge_input.value or 0)
            settings.echonet.water_heater_id = wh_id_input.value
            settings.echonet.water_heater_tank_capacity = int(wh_cap_input.value or 0)
            settings.echonet.water_heater_power_w = float(wh_power_input.value or 0)
            settings.echonet.smart_meter_id = sm_id_input.value
            settings.echonet.v2h_id = v2h_id_input.value
            settings.echonet.v2h_battery_capacity_wh = float(v2h_cap_input.value or 0)
            settings.echonet.v2h_charge_power_w = float(v2h_charge_input.value or 0)
            settings.echonet.v2h_discharge_power_w = float(v2h_discharge_input.value or 0)
            settings.echonet.ac_id = ac_id_input.value
            settings.echonet.ac_power_w = float(ac_power_input.value or 0)

            settings.save_to_yaml()
            ui.notify('Settings saved. Please restart the application.', type='positive')
        
        def reset_settings():
            user_path = "config/user_settings.yaml"
            if os.path.exists(user_path):
                os.remove(user_path)
                ui.notify('Settings reset to defaults. Please restart the application.', type='warning')
            else:
                ui.notify('Already using default settings.', type='info')

        with actions_row:
            ui.button('Save Settings', on_click=save_settings).classes('flex-1')
            ui.button('Reset to Defaults', on_click=reset_settings, color='red').classes('flex-1 ml-4')
