from nicegui import ui
from src.core.ems_manager import ems_manager

def create_gui():
    @ui.page('/')
    def index():
        ui.label('HEMS Emulator Dashboard').classes('text-2xl font-bold')
        
        with ui.row().classes('w-full justify-around'):
            # スマートメーター (Grid)
            with ui.card():
                ui.label('Grid (Smart Meter)')
                grid_label = ui.label('').classes('text-xl')
                ui.timer(1.0, lambda: grid_label.set_text(f'{ems_manager.grid.power_w:.1f} W'))

            # 太陽光 (Solar)
            with ui.card():
                ui.label('Solar Power')
                solar_label = ui.label('').classes('text-xl')
                ui.timer(1.0, lambda: solar_label.set_text(f'{ems_manager.solar.power_w:.1f} W'))

            # 家庭内負荷 (Load)
            with ui.card():
                ui.label('Home Load')
                load_label = ui.label('').classes('text-xl')
                ui.timer(1.0, lambda: load_label.set_text(f'{ems_manager.load.power_w:.1f} W'))

            # 蓄電池 (Battery)
            with ui.card():
                ui.label('Battery')
                battery_label = ui.label('').classes('text-xl')
                battery_soc = ui.linear_progress(value=0, show_value=False)
                ui.timer(1.0, lambda: [
                    battery_label.set_text(f'{ems_manager.battery.power_w:.1f} W'),
                    battery_soc.set_value(ems_manager.battery.soc_percent / 100.0)
                ])

        # 電力フローの簡易アニメーション（今後拡張）
        ui.label('Power Flow Visualization').classes('mt-8 text-lg font-semibold')
        with ui.row().classes('w-full h-40 bg-slate-100 items-center justify-center'):
            ui.label('Animation Placeholder').classes('animate-pulse')

    ui.run(port=8080, title='HEMS Emulator')

if __name__ in {"__main__", "gui"}:
    create_gui()
