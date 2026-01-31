import struct
from typing import Optional
from src.config.settings import settings
from .echonet import EchonetObjectInterface
from .models import Solar, Battery, SmartMeter
from src.core.smart_meter_consts import SMART_METER_STATIC_PROPS
from src.core.solar_consts import SOLAR_STATIC_PROPS
from src.core.battery_consts import BATTERY_STATIC_PROPS

class BaseAdapter(EchonetObjectInterface):
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
        elif epc == 0x83:
            try:
                return bytes.fromhex(settings.echonet.node_profile_id)
            except:
                return b'\xFE' + b'\x00'*16
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
        if epc in SMART_METER_STATIC_PROPS:
            return SMART_METER_STATIC_PROPS[epc]

        # 3. Fallback to Settings/Defaults (e.g. Status 80 if not in static)
        if epc == 0x80: 
            return b'\x30'
        elif epc == 0x83:
             try:
                return bytes.fromhex(settings.echonet.smart_meter_id)
             except:
                return b'\xFE' + b'\x00'*16

        return super().get_property(epc)

class SolarAdapter(BaseAdapter):
    def __init__(self, device: Solar):
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
        if epc in SOLAR_STATIC_PROPS:
            return SOLAR_STATIC_PROPS[epc]

        # 3. Fallback
        if epc == 0x80: 
            return b'\x30' if d.is_running else b'\x31'
        elif epc == 0x83: 
             try:
                return bytes.fromhex(settings.echonet.solar_id)
             except:
                return b'\xFE' + b'\x00'*16
            
        return super().get_property(epc)

class BatteryAdapter(BaseAdapter):
    def __init__(self, device: Battery):
        self.device = device
        
    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        # Merge static props keys with dynamic props
        # Dynamic overrides: E5 (SOC), DA (Operation Mode), D3 (Follow-up for issue)
        # Note: Previous E3 is removed unless in static props (User JSON doesn't have E3)
        dynamic_epcs = [0xE5, 0xDA, 0xD3]
        static_epcs = list(BATTERY_STATIC_PROPS.keys())
        return sorted(list(set(base + dynamic_epcs + static_epcs)))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        
        # 1. Dynamic Measurement Values
        if epc == 0xE5: # Remaining Capacity 3 (SOC %)
            # User JSON 229: [100]. We override.
            val = int(d.soc)
            return struct.pack("B", val)

        elif epc == 0xDA: # Operation Mode Setting
            # 0x41: Rapid Charge, 0x42: Charge, 0x43: Discharge, 0x44: Standby
            if d.is_charging:
                return b'\x42'
            elif d.is_discharging:
                return b'\x43'
            else:
                return b'\x44' # Standby
        
        elif epc == 0xD3: # Instantaneous Charge/Discharge Power
            # 4 bytes Int (W). Positive value.
            val = 0
            if d.is_charging: val = int(d.instant_charge_power)
            elif d.is_discharging: val = int(d.instant_discharge_power)
            return struct.pack(">I", val)

        # Note: 0xE2 (Rated Cap) is in static props (JSON 226). We use static value.
        # Note: 0xD3 (Op Status) is in static props (JSON 211, 4 bytes). We use static value.

        # 2. Static Properties
        if epc in BATTERY_STATIC_PROPS:
            # If D3 is in static, we override it above.
            return BATTERY_STATIC_PROPS[epc]
        
        # 3. Fallback
        if epc == 0x80: 
            # Status: ON (0x30) if running/charging/discharging, OFF (0x31) otherwise.
            # Usually standard says ON (0x30) during standby too if it's "On", but "Operation Status".
            # For battery, usually 0x30 always if system is on.
            # But user says "Always idle". Maybe they mean 0x31? Or 0x30 but inactive?
            # Let's link it to is_charging/discharging OR just is_running.
            # Requirement: "Also update 0x80 logic".
            status = b'\x30' if (d.is_running or d.is_charging or d.is_discharging) else b'\x31'
            return status

        elif epc == 0x83:
             try:
                return bytes.fromhex(settings.echonet.battery_id)
             except:
                return b'\xFE' + b'\x00'*16

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
                self.device.instant_charge_power = 1000.0 # Fixed per requirement
                self.device.instant_discharge_power = 0.0
            elif data == b'\x43': # Discharge
                self.device.is_charging = False
                self.device.is_discharging = True
                self.device.instant_charge_power = 0.0
                self.device.instant_discharge_power = 1000.0 # Fixed per requirement
            elif data == b'\x44': # Standby (Explicit)
                self.device.is_charging = False
                self.device.is_discharging = False
                self.device.instant_charge_power = 0.0
                self.device.instant_discharge_power = 0.0
            return True
        return super().set_property(epc, data)
