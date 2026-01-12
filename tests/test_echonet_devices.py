import struct
import unittest
from src.echonet.devices import SmartMeter
from src.core.ems_manager import ems_manager

class TestECHONETDevices(unittest.TestCase):
    def test_smart_meter_sync(self):
        meter = SmartMeter()
        ems_manager.grid.power_w = 1234.0
        
        meter.update_from_engine(ems_manager)
        
        # EPC 0xE7 (瞬時電力) が正しく更新されているか
        prop_val = meter.get_property(0xE7)
        power = struct.unpack(">i", prop_val)[0]
        self.assertEqual(power, 1234)

if __name__ == '__main__':
    unittest.main()
