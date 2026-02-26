from pydantic import BaseModel, Field
from enum import Enum
from typing import Literal

class DeviceType(str, Enum):
    SMART_METER = "smart_meter"
    SOLAR = "solar"
    BATTERY = "battery"
    ELECTRIC_WATER_HEATER = "electric_water_heater"
    V2H = "v2h"
    AIR_CONDITIONER = "air_conditioner"

class BaseDevice(BaseModel):
    device_id: str
    device_type: DeviceType
    is_running: bool = True

class SmartMeter(BaseDevice):
    device_type: Literal[DeviceType.SMART_METER] = DeviceType.SMART_METER
    
    # 瞬時電力計測値 (W)
    # 正: 買電 (Grid -> Home), 負: 売電 (Home -> Grid)
    instant_current_power: float = 0.0    
    
    # 積算電力量 (kWh)
    cumulative_power_buy_kwh: float = 0.0
    cumulative_power_sell_kwh: float = 0.0

class Solar(BaseDevice):
    device_type: Literal[DeviceType.SOLAR] = DeviceType.SOLAR
    
    # 瞬時発電電力 (W)
    instant_generation_power: float = 0.0
    
    # 積算発電電力量 (kWh)
    cumulative_generation_kwh: float = 0.0

class Battery(BaseDevice):
    device_type: Literal[DeviceType.BATTERY] = DeviceType.BATTERY
    
    # 運転モード (簡易エミュレーション用)
    # ECHONET Liteでは詳細な設定があるが、ここではコアロジック用フラグとして管理
    is_charging: bool = False
    is_discharging: bool = False
    
    # 充放電電力 (W)
    # 実際の制御では指示値と現在値があるが、ここでは実行値を保持
    instant_charge_power: float = 0.0
    instant_discharge_power: float = 0.0
    
    # 蓄電残量 (%)
    soc: float = 50.0 
    
    # 定格容量 (Wh)
    rated_capacity_wh: float = 10000.0 

    # 積算電力量 (Wh) - 内部管理用 (ECHONET Lite 0xA8, 0xA9 対応)
    cumulative_charge_wh: float = 0.0
    cumulative_discharge_wh: float = 0.0 

class ElectricWaterHeater(BaseDevice):
    device_type: Literal[DeviceType.ELECTRIC_WATER_HEATER] = DeviceType.ELECTRIC_WATER_HEATER
    
    # 運転状態 (0x80)
    # BaseDevice.is_running で管理 (True=0x30, False=0x31)

    # 沸き上げ自動設定 (0xB0)
    # 0x41: 自動, 0x42: 手動沸き上げ, 0x43: 手動沸き上げ停止
    auto_setting: int = 0x41 

    # 沸き上げ中状態 (0xB2)
    # 0x41: 沸き上げ中, 0x42: 非沸き上げ中
    is_heating: bool = False

    # 残湯量計測値 (0xE1)
    # 単位: 0.1L? ユーザーリクエストでは "10digit/hour" とある。
    # 生の値として保持する。
    remaining_hot_water: int = 0

    # タンク容量 (0xE2)
    # 単位: L? 生の値として保持する。
    tank_capacity: int = 370 
    
    # 湯沸かし電力 (W)
    # 設定値
    heating_power_w: float = 1000.0

    # 風呂自動モード設定 (0xE3)
    # 0x41: 自動, 0x42: 自動解除
    e3_bath_operation_status: int = 0x42

    # 昼間沸き増し設定 (0xC0)
    # 0x41: 昼間沸き増し許可, 0x42: 昼間沸き増し禁止
    c0_operation_status: int = 0x41


class AirConditioner(BaseDevice):
    device_type: Literal[DeviceType.AIR_CONDITIONER] = DeviceType.AIR_CONDITIONER

    # 運転モード設定 (0xB0)
    # 0x40: その他, 0x41: 自動, 0x42: 冷房, 0x43: 暖房, 0x44: 除湿, 0x45: 送風
    operation_mode: int = 0x43

    # 温度設定値 (0xB3) [°C]
    temperature_setting: int = 0x15  # 21°C

    # 風量設定 (0xA0)
    # 0x41: 自動, 0x31-0x38: 風量1-8
    air_flow_volume: int = 0x41

    # 節電動作設定 (0x8F)
    # 0x41: 節電動作中, 0x42: 非節電動作中
    power_saving_mode: int = 0x42

    # 瞬時消費電力計測値 (0x84) [W] - エンジンで計算
    instant_power_w: float = 0.0

    # 積算消費電力量計測値 (0x85) [Wh] - エンジンで積算 (0.001 kWh単位 = 1 Wh)
    cumulative_power_wh: float = 0.0


class V2H(BaseDevice):
    device_type: Literal[DeviceType.V2H] = DeviceType.V2H

    # 車両接続状態 (0xC7)
    # True=車両接続充放電可 (0x43), False=未接続 (0x30)
    vehicle_connected: bool = False

    # 運転モード設定 (0xDA)
    # 0x42: 充電, 0x43: 放電, 0x44: 待機, 0x47: 停止
    operation_mode: int = 0x47

    # 車載電池放電可能残容量1 (0xC2) [Wh]
    # 初期値は battery_capacity_wh の 50%（起動時に engine で設定）
    remaining_capacity_wh: float = 25000.0

    # 車載電池放電可能容量1 (0xC0) [Wh]（設定値）
    battery_capacity_wh: float = 50000.0

    # 積算電力量 (Wh) - 内部管理用 (ECHONET Lite 0xD8, 0xD6 対応)
    cumulative_charge_wh: float = 0.0
    cumulative_discharge_wh: float = 0.0

    # 充電電力設定値 (0xEB) [W]
    charge_power_w: float = 3000.0

    # 放電電力設定値 (0xEC) [W]
    discharge_power_w: float = 3000.0

    # エンジン内部計算用（グリッド計算式に使用）
    # 今サイクルの実際の充電電力 [W]（充電中のみ正値）
    current_charge_w: float = 0.0
    # 今サイクルの実際の放電電力 [W]（放電中のみ正値）
    current_discharge_w: float = 0.0
