import struct
from typing import Optional
from .echonet import EchonetObjectInterface
from .models import Solar, Battery

class BaseAdapter(EchonetObjectInterface):
    def get_property(self, epc: int) -> Optional[bytes]:
        return None
    def set_property(self, epc: int, data: bytes) -> bool:
        return False

class SolarAdapter(BaseAdapter):
    def __init__(self, device: Solar):
        self.device = device
        
    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        if epc == 0x80: # Operation Status (0x30: ON, 0x31: OFF)
            return b'\x30' if d.is_running else b'\x31'
            
        elif epc == 0xE0: # Instantaneous Power Generation (W)
            # Unit: W. 2 bytes? ECHONET spec says 0xE0 can be variable but usually 2 or 4.
            # Solar spec: 0xE0 (Measured instantaneous amount of electricity generated) is 2 bytes (unsigned short).
            # Max 65535W.
            val = int(d.instant_generation_power)
            return struct.pack(">H", min(val, 65535))
            
        elif epc == 0xE1: # Cumulative Generation (0.001 kWh)
            # 4 bytes unsigned long
            val = int(d.cumulative_generation_kwh * 1000)
            return struct.pack(">L", min(val, 0xFFFFFFFF))
            
        return None

class BatteryAdapter(BaseAdapter):
    def __init__(self, device: Battery):
        self.device = device
        
    def get_property(self, epc: int) -> Optional[bytes]:
        d = self.device
        if epc == 0x80: 
            return b'\x30'
            
        elif epc == 0xE3: # Remaining Capacity (SOC) %
            # 1 byte
            val = int(d.soc)
            return struct.pack("B", val)
            
        elif epc == 0xD3: # Working Operation Status
            # 0x41: Idle, 0x42: Charge, 0x43: Discharge, 0x40: Other
            if d.is_charging: return b'\x42'
            if d.is_discharging: return b'\x43'
            return b'\x41' # Idle
            
        elif epc == 0xE2: # Rated Capacity (Wh)
            # Property: 0xE2? Check Spec.
            # Storage Battery: 0xE2 = Measured remaining capacity (Wh)?
            # 0xE0: Measured instantaneous charge/discharge electric energy
            pass

        return None
        
    def set_property(self, epc: int, data: bytes) -> bool:
        if epc == 0x80:
            if data == b'\x30': self.device.is_running = True
            elif data == b'\x31': self.device.is_running = False
            return True
        return False
