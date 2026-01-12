import pandas as pd
import asyncio
from datetime import datetime, timedelta
from src.core.ems_manager import ems_manager

class ScenarioPlayer:
    """CSVシナリオに基づきシミュレーションを進行させる"""
    def __init__(self, scenario_path: str):
        self.scenario_path = scenario_path
        self.df = None
        self.current_index = 0
        self.is_running = False

    def load_scenario(self):
        """CSVからシナリオデータを読み込む"""
        # CSVフォーマット想定: timestamp, load_w, solar_w
        self.df = pd.read_csv(self.scenario_path)
        # TODO: 時刻のパースなどが必要な場合はここで処理

    async def start(self):
        """シナリオ実行ループ"""
        if self.df is None:
            self.load_scenario()
        
        self.is_running = True
        last_time = datetime.now()

        while self.is_running and self.current_index < len(self.df):
            row = self.df.iloc[self.current_index]
            
            # 各コンポーネントの値を更新
            ems_manager.load.power_w = float(row['load_w'])
            ems_manager.solar.power_w = float(row['solar_w'])
            
            # 1ステップ進める (例: 1秒ごとに更新と仮定)
            now = datetime.now()
            delta = (now - last_time).total_seconds()
            ems_manager.step(delta)
            
            last_time = now
            self.current_index += 1
            
            await asyncio.sleep(1) # 1秒周期

    def stop(self):
        self.is_running = False

# シナリオプレイヤーのインスタンス（本来は引数でパス指定）
# scenario_player = ScenarioPlayer("data/scenarios/default_day.csv")
