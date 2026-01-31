from nicegui import ui
import src.core.echonet_consts as ec
from src.core.echonet import wifi_echonet_ctrl, wisun_echonet_ctrl

def render():
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
                                
                                # Get supported EPCs
                                epcs = []
                                if hasattr(obj, '_get_supported_epcs'):
                                    epcs = obj._get_supported_epcs()
                                else:
                                    # Fallback
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

            render_controller("Wi-Fi (UDP port 3610)", wifi_echonet_ctrl)
            render_controller("Wi-SUN (B-Route Serial)", wisun_echonet_ctrl)

        with inspector_actions:
            ui.button('Refresh Properties', on_click=refresh_inspector, icon='refresh')
        
        # Initial Load (Delayed to ensure startup finished)
        ui.timer(1.0, refresh_inspector, once=True)
