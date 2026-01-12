import asyncio
import signal
from src.core.ems_manager import ems_manager
from src.core.scenario_player import ScenarioPlayer
from src.echonet.stack import echonet_stack
from src.echonet.devices import SmartMeter, SolarPower, Battery
from src.gui.dashboard import create_gui

async def main():
    print("Starting HEMS Emulator...")

    # 1. 機器の初期化とスタックへの登録
    meter = SmartMeter(ins_id=1)
    solar = SolarPower(ins_id=1)
    battery = Battery(ins_id=1)
    
    echonet_stack.register_object(meter)
    echonet_stack.register_object(solar)
    echonet_stack.register_object(battery)

    # 2. ECHONET Lite スタックの開始
    await echonet_stack.start()

    # 3. シナリオプレイヤーの開始
    player = ScenarioPlayer("data/scenarios/default_day.csv")
    asyncio.create_task(player.start())

    # 4. エンジンの値を機器プロパティに同期させるループ
    async def sync_loop():
        while True:
            meter.update_from_engine(ems_manager)
            solar.update_from_engine(ems_manager)
            battery.update_from_engine(ems_manager)
            await asyncio.sleep(1)

    asyncio.create_task(sync_loop())

    # 5. GUIの起動 (ui.run は内部でループを回すが、asyncioとの兼ね合いで調整が必要な場合あり)
    # 本来は main.py から全コンポーネントをオーケストレートする
    create_gui()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
