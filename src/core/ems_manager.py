import asyncio
from dataclasses import dataclass

@dataclass
class DeviceState:
    power_w: float = 0.0  # 瞬時電力 (W)
    energy_kwh: float = 0.0  # 積算電力量 (kWh)
    soc_percent: float = 0.0  # 蓄電残量 (%)

class EMSManager:
    """家庭内の電力収支を管理するコアエンジン"""
    def __init__(self):
        # 各機器の状態
        self.grid = DeviceState()    # スマートメーター (正: 買電, 負: 売電)
        self.load = DeviceState()    # 負荷
        self.solar = DeviceState()   # 太陽光
        self.battery = DeviceState() # 蓄電池 (正: 充電, 負: 放電)

        # 物理制約
        self.battery_capacity_kwh = 10.0
        self.battery_max_power_w = 5000.0

    def update_balance(self):
        """
        P_grid = (P_load + P_charge) - (P_solar + P_discharge)
        に基づきスマートメーターの値を更新する
        """
        # P_charge と P_discharge は蓄電池の power_w で表現 (正が充電、負が放電)
        p_load = self.load.power_w
        p_charge_discharge = self.battery.power_w
        p_solar = self.solar.power_w
        
        # グリッド電力の計算
        self.grid.power_w = (p_load + p_charge_discharge) - p_solar

    def step(self, delta_sec: float):
        """
        時間の経過による積算電力量とSOCの更新
        """
        hours = delta_sec / 3600.0

        # 蓄電池のSOC更新 (簡易モデル)
        if self.battery.power_w != 0:
            energy_delta = (self.battery.power_w / 1000.0) * hours
            new_energy = self.battery.energy_kwh + energy_delta
            
            # ガードロジック: 容量制限
            if new_energy < 0:
                new_energy = 0
                self.battery.power_w = 0 # 放電不可
            elif new_energy > self.battery_capacity_kwh:
                new_energy = self.battery_capacity_kwh
                self.battery.power_w = 0 # 充電不可
                
            self.battery.energy_kwh = new_energy
            self.battery.soc_percent = (self.battery.energy_kwh / self.battery_capacity_kwh) * 100.0

        # 各機器の積算電力量の更新 (スマートメーターなど)
        # TODO: 正方向と負方向（買電・売電）を分けて保持するロジックが必要（ECHONET Lite準拠のため）
        self.update_balance()

ems_manager = EMSManager()
