import struct
from typing import Optional
from src.config.settings import settings
from .echonet import EchonetObjectInterface
from .models import Solar, Battery, SmartMeter, ElectricWaterHeater, V2H, AirConditioner
from src.core.smart_meter_consts import SMART_METER_STATIC_PROPS
from src.core.solar_consts import SOLAR_STATIC_PROPS
from src.core.battery_consts import BATTERY_STATIC_PROPS
from src.core.water_heater_consts import WATER_HEATER_STATIC_PROPS
from src.core.v2h_consts import V2H_STATIC_PROPS
from src.core.aircon_consts import AIRCON_STATIC_PROPS

class BaseAdapter(EchonetObjectInterface):
    def __init__(self, config_id: str = None):
        self._config_id = config_id

    def _build_property_map(self, epcs: list[int]) -> bytes:
        # ECHONET Lite Property Map Format
        # If count < 16: Byte 1 = count, Bytes 2..n = EPCs
        # If count >= 16: Byte 1 = count, Bytes 2..17 = Bitmap (EPC 0x80-0x87, ... 0xF8-0xFF)
        
        count = len(epcs)
        if count < 16:
            return bytes([count] + epcs)
        else:
            # Bitmap implementation
            bitmap = bytearray(16)
            for epc in epcs:
                if 0x80 <= epc <= 0xFF:
                    idx = (epc - 0x80) // 8
                    bit = 7 - ((epc - 0x80) % 8)
                    if 0 <= idx < 16:
                        bitmap[idx] |= (1 << bit)
            return bytes([count]) + bitmap

    def _get_supported_epcs(self) -> list[int]:
        # Subclasses should override this
        return [0x80, 0x82, 0x88, 0x8A, 0x9D, 0x9E, 0x9F]

    def get_property(self, epc: int) -> Optional[bytes]:
        # Common Properties
        if epc == 0x88: # Fault Status (0x41: Fault, 0x42: No Fault)
            return b'\x42'
        elif epc == 0x8A: # Manufacturer Code
            # 3 bytes
            try:
                code_int = int(settings.echonet.maker_code, 16)
                return struct.pack(">I", code_int)[1:] 
            except:
                return b'\x00\x00\x00'
        elif epc == 0x83: # Identification Number
            try:
                if self._config_id:
                    return bytes.fromhex(self._config_id)
            except:
                pass
            return b'\xFE' + b'\x00'*16
            
        elif epc == 0x9D: # Status Change Announcement Property Map
            return self._build_property_map([0x80, 0x88])
        elif epc == 0x9E: # Set Property Map
            return self._build_property_map([0x80]) 
        elif epc == 0x9F: # Get Property Map
            return self._build_property_map(self._get_supported_epcs())
        
        return None

    def set_property(self, epc: int, data: bytes) -> bool:
        return False

class NodeProfileAdapter(BaseAdapter):
    def __init__(self, instances: list[tuple[int, int, int]] = None):
        super().__init__(settings.echonet.node_profile_id)
        if instances is None:
            # Default: Solar and Battery (for backward compatibility or default wifi)
            # Solar (02, 79, 01), Battery (02, 7D, 01)
            self._instances = [
                (0x02, 0x79, 0x01),
                (0x02, 0x7D, 0x01)
            ]
        else:
            self._instances = instances

    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        return sorted(list(set(base + [0x83, 0xD5, 0xD6])))

    def get_property(self, epc: int) -> Optional[bytes]:
        if epc == 0x80: return b'\x30'
        elif epc == 0x82: return b'\x01\x0A\x01\x00'
        elif epc == 0xD5 or epc == 0xD6:
            return self._get_instance_list()
        
        return super().get_property(epc)

    def _get_instance_list(self) -> bytes:
        # Format: Count(1B), [ClassGroup(1B), ClassCode(1B), InstanceCode(1B)] * N
        count = len(self._instances)
        data = bytearray([count])
        for group, code, inst in self._instances:
            data.extend([group, code, inst])
        return bytes(data)

class SmartMeterAdapter(BaseAdapter):
    def __init__(self, device: SmartMeter):
        super().__init__(settings.echonet.smart_meter_id)
        self.device = device
        
    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        # Merge static props keys with dynamic props
        # Dynamic overrides: E0, E3, E7
        dynamic_epcs = [0xE0, 0xE3, 0xE7]
        static_epcs = list(SMART_METER_STATIC_PROPS.keys())
        return sorted(list(set(base + dynamic_epcs + static_epcs)))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        
        # 1. Dynamic Measurement Values (Priority: Simulation Model)
        # These must reflect the current simulation state, overriding static data if any
        if epc == 0xE7: # Instantaneous Electric Power (W)
            val = int(d.instant_current_power)
            return struct.pack(">i", val)
            
        elif epc == 0xE0: # Cumulative Amount (Buy)
            val = int(d.cumulative_power_buy_kwh)
            return struct.pack(">L", min(val, 0xFFFFFFFF))
            
        elif epc == 0xE3: # Cumulative Amount (Sell)
            val = int(d.cumulative_power_sell_kwh)
            return struct.pack(">L", min(val, 0xFFFFFFFF))

        # 2. Static Properties from User Data (Priority: User JSON)
        # Includes ID(83), Unit(E1), Digits(D7), etc.
        # FIX: Force use of settings for Maker Code (0x8A) and ID (0x83) even if present in static props
        if epc == 0x8A or epc == 0x83:
            return super().get_property(epc)
            
        if epc in SMART_METER_STATIC_PROPS:
            return SMART_METER_STATIC_PROPS[epc]

        # 3. Fallback to Settings/Defaults (e.g. Status 80 if not in static)
        if epc == 0x80: 
            return b'\x30'


        return super().get_property(epc)

class SolarAdapter(BaseAdapter):
    def __init__(self, device: Solar):
        super().__init__(settings.echonet.solar_id)
        self.device = device
        
    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        # Merge static props keys with dynamic props
        # Dynamic overrides: E0, E1
        dynamic_epcs = [0xE0, 0xE1]
        static_epcs = list(SOLAR_STATIC_PROPS.keys())
        return sorted(list(set(base + dynamic_epcs + static_epcs)))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        
        # 1. Dynamic Measurement Values
        if epc == 0xE0: # Instantaneous Power Generation (W)
            # User JSON has 2 bytes [0,0]. We override with dynamic value.
            val = int(d.instant_generation_power)
            return struct.pack(">H", min(val, 65535))
            
        elif epc == 0xE1: # Cumulative Generation
            # User JSON has 4 bytes. 
            val = int(d.cumulative_generation_kwh * 1000) # Assuming 0.001kWh unit? Or 1?
            # User JSON 225 data: [0,2,39,247] => 147447. If unit 0.001 -> 147kWh. Plausible.
            return struct.pack(">L", min(val, 0xFFFFFFFF))
            
        # 2. Static Properties
        # FIX: Force use of settings for Maker Code (0x8A) and ID (0x83)
        if epc == 0x8A or epc == 0x83:
            return super().get_property(epc)

        if epc in SOLAR_STATIC_PROPS:
            return SOLAR_STATIC_PROPS[epc]

        # 3. Fallback
        if epc == 0x80: 
            return b'\x30' if d.is_running else b'\x31'

            
        return super().get_property(epc)

class BatteryAdapter(BaseAdapter):
    def __init__(self, device: Battery):
        super().__init__(settings.echonet.battery_id)
        self.device = device
        
    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        # Merge static props keys with dynamic props
        # Dynamic overrides: CF (Working Operation Status), DA (Operation Mode Setting), D3 (Follow-up for issue), E2 (Wh), E4 (SOC)
        # Added: A4, A5, A8, A9, D0
        dynamic_epcs = [0xCF, 0xD0, 0xDA, 0xD3, 0xE2, 0xE4, 0xA4, 0xA5, 0xA8, 0xA9]
        static_epcs = list(BATTERY_STATIC_PROPS.keys())
        return sorted(list(set(base + dynamic_epcs + static_epcs)))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        
        # 1. Dynamic Measurement Values
        if epc == 0xE4: # Remaining stored electricity 3 (SOC %) 
            # 0-100%, 1 byte
            val = int(d.soc)
            return struct.pack("B", val)

        elif epc == 0xA4: # AC Chargeable Electric Energy (Wh)
            # Rated Capacity - Current Stored Wh
            current_wh = d.rated_capacity_wh * d.soc / 100.0
            val = int(d.rated_capacity_wh - current_wh)
            return struct.pack(">L", max(0, min(val, 0xFFFFFFFF)))

        elif epc == 0xA5: # AC Dischargeable Electric Energy (Wh)
            # Same as current stored Wh (E2)
            val = int(d.rated_capacity_wh * d.soc / 100.0)
            return struct.pack(">L", min(val, 0xFFFFFFFF))
            
        elif epc == 0xA8: # AC cumulative charging electric energy (Wh)
            val = int(d.cumulative_charge_wh)
            return struct.pack(">L", min(val, 0xFFFFFFFF))

        elif epc == 0xA9: # AC cumulative discharging electric energy (Wh)
            val = int(d.cumulative_discharge_wh)
            return struct.pack(">L", min(val, 0xFFFFFFFF))

        elif epc == 0xE2: # Remaining stored electricity 1 (Wh)
            # 4 bytes unsigned long (Wh)
            # Calculate from rated_capacity_wh * soc / 100
            wh_val = int(d.rated_capacity_wh * d.soc / 100.0)
            return struct.pack(">L", wh_val)

        elif epc == 0xD0: # Rated Electric Energy (Wh)
            val = int(d.rated_capacity_wh)
            return struct.pack(">L", max(0, min(val, 0xFFFFFFFF)))

        elif epc == 0xDA or epc == 0xCF: # Operation Mode Setting or Working Operation Status
            # 0x41: Rapid Charge, 0x42: Charge, 0x43: Discharge, 0x44: Standby
            if d.is_charging:
                return b'\x42'
            elif d.is_discharging:
                return b'\x43'
            else:
                return b'\x44' # Standby
        
        elif epc == 0xD3: # Instantaneous Charge/Discharge Power
            # 4 bytes Signed Int (W). Positive: Charge, Negative: Discharge
            val = 0
            if d.is_charging: val = int(d.instant_charge_power)
            elif d.is_discharging: val = -int(d.instant_discharge_power)
            return struct.pack(">i", val)

        # 2. Static Properties
        if epc == 0x8A or epc == 0x83: # FIX: Force use of settings for Maker Code and ID
            return super().get_property(epc)

        if epc == 0x80: 
            # Status: ON (0x30) if running/charging/discharging, OFF (0x31) otherwise.
            status = b'\x30' if (d.is_running or d.is_charging or d.is_discharging) else b'\x31'
            return status

        if epc in BATTERY_STATIC_PROPS:
            # If D3 is in static, we override it above.
            return BATTERY_STATIC_PROPS[epc]
        
        # 3. Fallback




        return super().get_property(epc)
        
    def set_property(self, epc: int, data: bytes) -> bool:
        if epc == 0x80:
            if data == b'\x30': self.device.is_running = True
            elif data == b'\x31': self.device.is_running = False
            return True
        elif epc == 0xDA: # Operation Mode Setting
            if data == b'\x42' or data == b'\x41': # Charge or Rapid Charge
                self.device.is_charging = True
                self.device.is_discharging = False
                self.device.instant_charge_power = self.device.max_charge_power_w
                self.device.instant_discharge_power = 0.0
            elif data == b'\x43': # Discharge
                self.device.is_charging = False
                self.device.is_discharging = True
                self.device.instant_charge_power = 0.0
                self.device.instant_discharge_power = self.device.max_discharge_power_w
            elif data == b'\x44': # Standby (Explicit)
                self.device.is_charging = False
                self.device.is_discharging = False
                self.device.instant_charge_power = 0.0
                self.device.instant_discharge_power = 0.0
            return True
        return super().set_property(epc, data)

class ElectricWaterHeaterAdapter(BaseAdapter):
    def __init__(self, device: ElectricWaterHeater):
        super().__init__(settings.echonet.water_heater_id)
        self.device = device

    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        # Merge static props keys with dynamic props
        # Dynamic overrides: 0x80, 0xB0, 0xB2, 0xE1, 0xE2
        dynamic_epcs = [0x80, 0xB0, 0xB2, 0xE1, 0xE2, 0xE3, 0xC0]
        static_epcs = list(WATER_HEATER_STATIC_PROPS.keys())
        return sorted(list(set(base + dynamic_epcs + static_epcs)))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        
        # 1. Dynamic Values
        if epc == 0x80: # Status
            return b'\x30' if d.is_running else b'\x31'
            
        elif epc == 0xB0: # Auto Setting
            # 0x41: Auto, 0x42: Manual Start, 0x43: Manual Stop
            return bytes([d.auto_setting])
            
        elif epc == 0xB2: # Heating Status
            # 0x41: Heating, 0x42: Not Heating (as per request)
            return b'\x41' if d.is_heating else b'\x42'
            
        elif epc == 0xE1: # Remaining Hot Water
            # User request: "raw value"
            # It seems user treats 0xE1 as a number corresponding to digits. 10digits/hour.
            # ECHONET spec says 0xE1 is "Measured remaining hot water amount".
            # User provided prop default: 0xE1: [0, 185].
            # We return as 2 bytes? Or 1?
            # User provided props has 0xE1: [0, 185] -> 2 bytes.
            val = int(d.remaining_hot_water)
            return struct.pack(">H", val)

        elif epc == 0xE2: # Tank Capacity
            # User provided prop default: 0xE2: [1, 114] -> 370. 2 bytes.
            val = int(d.tank_capacity)
            return struct.pack(">H", val)

        elif epc == 0xE3: # Bath Operation Status
            # 0x41: ON, 0x42: OFF (or similar based on app usage)
            return bytes([d.e3_bath_operation_status])

        elif epc == 0xC0: # Operation Status / Initial Setting
            return bytes([d.c0_operation_status])

        # 2. Static Properties
        if epc == 0x8A or epc == 0x83: # FIX: Force use of settings for Maker Code and ID
            return super().get_property(epc)

        if epc in WATER_HEATER_STATIC_PROPS:
            return WATER_HEATER_STATIC_PROPS[epc]

        return super().get_property(epc)

    def set_property(self, epc: int, data: bytes) -> bool:
        if epc == 0x80:
            if data == b'\x30': self.device.is_running = True
            elif data == b'\x31': self.device.is_running = False
            return True
        elif epc == 0xB0: # Auto Setting
            val = data[0]
            if val in [0x41, 0x42, 0x43]:
                # User request logic:
                # If set to 0x43 (Stop) or 0x41 (Auto), B2 -> 0x42 (Not Heating)
                # If set to 0x42 (Start), B2 -> 0x41 (Heating)
                # We update the model, engine loop will handle progressive changes (E1).
                # But immediate state change is requested?
                # "When 0xB0 is ... 0x43, ... 0xE1 decreases..." -> Engines job.
                # "When 0xB0 is ... 0x42, ... 0xE1 increases..."
                
                # Immediate reaction to Set:
                self.device.auto_setting = val
                if val == 0x42: # Manual Start
                     self.device.is_heating = True
                elif val == 0x43 or val == 0x41: # Manual Stop
                     self.device.is_heating = False
                     
                return True
                
        elif epc == 0xE3: # Bath Operation Status
            self.device.e3_bath_operation_status = data[0]
            return True

        elif epc == 0xC0: # Operation Status
             self.device.c0_operation_status = data[0]
             return True
        return super().set_property(epc, data)


class V2HAdapter(BaseAdapter):
    """電気自動車充放電器 (V2H) クラ스コード 0x027E のアダプター"""

    def __init__(self, device: V2H):
        super().__init__(settings.echonet.v2h_id)
        self.device = device

    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        dynamic_epcs = [
            0x80, 0x83, 0x8A,
            0xC0, 0xC2, 0xC7,
            0xD0, 0xD3, 0xD6, 0xD8, 0xDA,
            0xE1, 0xE2, 0xE4, 0xEB, 0xEC,
        ]
        static_epcs = list(V2H_STATIC_PROPS.keys())
        return sorted(list(set(base + dynamic_epcs + static_epcs)))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        import logging
        logger = logging.getLogger(__name__)

        # --- 動的プロパティ ---
        if epc == 0x80:  # 動作状態
            return b'\x30' if d.is_running else b'\x31'

        elif epc == 0xC0 or epc == 0xD0:  # 車載電池放電可能容量1 (Wh) or 車載電池の使用容量値 1
            val = int(d.battery_capacity_wh)
            return struct.pack('>L', max(0, min(val, 0xFFFFFFFF)))

        elif epc == 0xC2 or epc == 0xE2:  # 車載電池放電可能残容量1 (Wh) or 車載電池の電池残容量 1
            val = int(d.remaining_capacity_wh)
            return struct.pack('>L', max(0, min(val, 0xFFFFFFFF)))

        elif epc == 0xE4:  # 車載電池の電池残容量 2 (%) 1バイト
            if d.battery_capacity_wh > 0:
                val = int((d.remaining_capacity_wh / d.battery_capacity_wh) * 100)
            else:
                val = 0
            return struct.pack('B', max(0, min(val, 100)))

        elif epc == 0xC7:  # 車両接続・充放電可否状態
            if not d.vehicle_connected:
                return b'\x30'  # 未接続
            return b'\x43'  # 接続、充放電可

        elif epc == 0xD3:  # 瞬時充放電電力計測値 (W) 符号付き4バイト
            # 設定値ではなく、エンジンが計算した現在の「実測値」を返すように修正
            if d.operation_mode == 0x42:  # 充電
                val = int(d.current_charge_w)
            elif d.operation_mode == 0x43:  # 放電
                val = -int(d.current_discharge_w)
            else:
                val = 0
            return struct.pack('>i', val)

        elif epc == 0xD8:  # 積算充電電力量1 (Wh) 4バイト
            val = int(d.cumulative_charge_wh)
            return struct.pack('>L', max(0, min(val, 0xFFFFFFFF)))

        elif epc == 0xD6:  # 積算放電電力量1 (Wh) 4バイト
            val = int(d.cumulative_discharge_wh)
            return struct.pack('>L', max(0, min(val, 0xFFFFFFFF)))

        elif epc == 0xDA:  # 運転モード設定
            if not d.vehicle_connected:
                return b'\x47'  # 未接続時は常に停止
            return bytes([d.operation_mode])

        elif epc == 0xE1:  # 運転動作状態（運転モード設定に連動）
            return bytes([d.operation_mode])

        elif epc == 0xEB:  # 充電電力設定値 (W)
            val = int(d.charge_power_w)
            return struct.pack('>L', max(0, min(val, 0xFFFFFFFF)))

        elif epc == 0xEC:  # 放電電力設定値 (W)
            val = int(d.discharge_power_w)
            return struct.pack('>L', max(0, min(val, 0xFFFFFFFF)))

        # --- Settings 経由プロパティ ---
        if epc == 0x8A or epc == 0x83:
            return super().get_property(epc)

        # --- 静的プロパティ ---
        if epc in V2H_STATIC_PROPS:
            return V2H_STATIC_PROPS[epc]

        return super().get_property(epc)

    def set_property(self, epc: int, data: bytes) -> bool:
        d = self.device
        import logging
        logger = logging.getLogger(__name__)

        if epc == 0x80:  # 動作状態
            if data == b'\x30':
                d.is_running = True
            elif data == b'\x31':
                d.is_running = False
            return True

        elif epc == 0xCD:  # 車両接続確認（トグル）
            if not d.vehicle_connected:
                # 未接続 -> 接続
                d.vehicle_connected = True
                d.operation_mode = 0x44  # 待機
                logger.info("V2H: Vehicle connected. Mode -> Standby (0x44)")
            return True

        elif epc == 0xDA:  # 運転モード設定
            if not d.vehicle_connected:
                logger.warning("V2H: SET 0xDA rejected (vehicle not connected)")
                return False  # 未接続時は失敗
            val = data[0] if data else 0
            if val not in (0x42, 0x43, 0x44, 0x47):  # 充電/放電/待機/停止のみ許可
                logger.warning(f"V2H: SET 0xDA rejected (invalid value: 0x{val:02X})")
                return False
            d.operation_mode = val
            logger.info(f"V2H: Operation mode set to 0x{val:02X}")
            if val == 0x47:  # 停止
                d.vehicle_connected = False # 未接続
            return True

        elif epc == 0xEB:  # 充電電力設定値 (W)
            if len(data) >= 4:
                val = struct.unpack('>L', data[:4])[0]
                d.charge_power_w = float(val)
            return True

        elif epc == 0xEC:  # 放電電力設定値 (W)
            if len(data) >= 4:
                val = struct.unpack('>L', data[:4])[0]
                d.discharge_power_w = float(val)
            return True

        return super().set_property(epc, data)


class AirConditionerAdapter(BaseAdapter):
    """家庭用エアコン (0x0130) アダプター"""

    def __init__(self, device: AirConditioner):
        super().__init__(settings.echonet.ac_id)
        self.device = device

    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        dynamic_epcs = [0x80, 0x84, 0x85, 0x8F, 0xA0, 0xB0, 0xB3]
        static_epcs = list(AIRCON_STATIC_PROPS.keys())
        return sorted(list(set(base + dynamic_epcs + static_epcs)))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device

        # Settings 優先プロパティ (0x8A: Maker Code, 0x83: Identification Number)
        if epc in (0x8A, 0x83):
            return super().get_property(epc)

        # 動的プロパティ
        if epc == 0x80:  # 動作状態
            return b'\x30' if d.is_running else b'\x31'
        elif epc == 0x84:  # 瞬時消費電力計測値 (2 bytes unsigned, W)
            return struct.pack(">H", min(int(d.instant_power_w), 65533))
        elif epc == 0x85:  # 積算消費電力量計測値 (4 bytes unsigned, 0.001 kWh単位 = Wh)
            return struct.pack(">L", min(int(d.cumulative_power_wh), 0xFFFFFFFE))
        elif epc == 0x8F:  # 節電動作設定
            return bytes([d.power_saving_mode])
        elif epc == 0xA0:  # 風量設定
            return bytes([d.air_flow_volume])
        elif epc == 0xB0:  # 運転モード設定
            return bytes([d.operation_mode])
        elif epc == 0xB3:  # 温度設定値
            return bytes([d.temperature_setting])

        # 静的プロパティ
        if epc in AIRCON_STATIC_PROPS:
            return AIRCON_STATIC_PROPS[epc]

        return super().get_property(epc)

    def set_property(self, epc: int, data: bytes) -> bool:
        d = self.device
        if epc == 0x80:  # 動作状態
            if data == b'\x30':
                d.is_running = True
            elif data == b'\x31':
                d.is_running = False
            return True
        elif epc == 0x8F:  # 節電動作設定
            if data and data[0] in (0x41, 0x42):
                d.power_saving_mode = data[0]
                return True
        elif epc == 0xB0:  # 運転モード設定
            if data and data[0] in (0x40, 0x41, 0x42, 0x43, 0x44, 0x45):
                d.operation_mode = data[0]
                return True
        elif epc == 0xB3:  # 温度設定値
            if data:
                d.temperature_setting = data[0]
                return True
        elif epc == 0xA0:  # 風量設定
            if data:
                d.air_flow_volume = data[0]
                return True
        return super().set_property(epc, data)
