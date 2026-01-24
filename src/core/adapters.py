import struct
from typing import Optional
from src.config.settings import settings
from .echonet import EchonetObjectInterface
from .models import Solar, Battery, SmartMeter
from src.core.smart_meter_consts import SMART_METER_STATIC_PROPS

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
        return sorted(list(set(base + [0x83, 0xE0, 0xE1])))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        
        # Device Specific
        if epc == 0x80: 
            return b'\x30' if d.is_running else b'\x31'
        elif epc == 0x83: # Identification Number
             try:
                return bytes.fromhex(settings.echonet.solar_id)
             except:
                return b'\xFE' + b'\x00'*16
            
        elif epc == 0xE0: # Instantaneous Power Generation (W)
            val = int(d.instant_generation_power)
            return struct.pack(">H", min(val, 65535))
            
        elif epc == 0xE1: # Cumulative Generation (0.001 kWh)
            val = int(d.cumulative_generation_kwh * 1000)
            return struct.pack(">L", min(val, 0xFFFFFFFF))
            
        return super().get_property(epc)

class BatteryAdapter(BaseAdapter):
    def __init__(self, device: Battery):
        self.device = device
        
    def _get_supported_epcs(self) -> list[int]:
        base = super()._get_supported_epcs()
        return sorted(list(set(base + [0x83, 0xD3, 0xE2, 0xE3])))

    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        
        if epc == 0x80: 
            return b'\x30'
        elif epc == 0x83:
             try:
                return bytes.fromhex(settings.echonet.battery_id)
             except:
                return b'\xFE' + b'\x00'*16
            
        elif epc == 0xE3: # Remaining Capacity (SOC) %
            val = int(d.soc)
            return struct.pack("B", val)
            
        elif epc == 0xD3: # Working Operation Status
            if d.is_charging: return b'\x42'
            if d.is_discharging: return b'\x43'
            return b'\x41' # Idle
            
        elif epc == 0xE2: # Rated Capacity (Wh)
            val = int(settings.echonet.battery_rated_capacity_wh)
            return struct.pack(">L", min(val, 0xFFFFFFFF))

        return super().get_property(epc)
        
    def set_property(self, epc: int, data: bytes) -> bool:
        if epc == 0x80:
            if data == b'\x30': self.device.is_running = True
            elif data == b'\x31': self.device.is_running = False
            return True
        return super().set_property(epc, data)
