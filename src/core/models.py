from pydantic import BaseModel, Field
from enum import Enum
from typing import Literal

class DeviceType(str, Enum):
    SMART_METER = "smart_meter"
    SOLAR = "solar"
    BATTERY = "battery"
    ELECTRIC_WATER_HEATER = "electric_water_heater"

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

