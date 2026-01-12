import unittest
from src.core.ems_manager import EMSManager

class TestEMSManager(unittest.TestCase):
    def setUp(self):
        self.ems = EMSManager()

    def test_power_balance(self):
        # P_grid = (P_load + P_charge) - (P_solar + P_discharge)
        self.ems.load.power_w = 1000
        self.ems.solar.power_w = 400
        self.ems.battery.power_w = 200 # 充電中(+200)
        
        self.ems.update_balance()
        # (1000 + 200) - 400 = 800
        self.assertEqual(self.ems.grid.power_w, 800)

    def test_battery_soc_guard(self):
        self.ems.battery.energy_kwh = 10.0 # Full
        self.ems.battery_capacity_kwh = 10.0
        self.ems.battery.power_w = 1000.0 # 充電しようとする
        
        self.ems.step(3600) # 1時間経過
        # SOCが100%なので充電されない (power_wが0になる)
        self.assertEqual(self.ems.battery.power_w, 0)
        self.assertEqual(self.ems.battery.energy_kwh, 10.0)

if __name__ == '__main__':
    unittest.main()
