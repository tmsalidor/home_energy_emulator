import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.models import FuelCell
from src.core.adapters import FuelCellAdapter
from src.core.engine import engine
from src.config.settings import settings
import struct

def test_fuel_cell():
    print("Testing Fuel Cell Logic...")
    
    # Enable test scenario
    engine.use_scenario = False
    engine.fuel_cell.is_running = True
    engine.fuel_cell.power_generation_setting = 0x41
    
    # Disable other devices to isolate power calculations
    engine.air_conditioner.is_running = False
    engine.water_heater.is_running = False
    engine.battery.operation_mode = 0x44
    engine.v2h.operation_mode = 0x44
    
    # 1. 逆潮流不可 (interconnection_status != 0)
    engine.fuel_cell.interconnection_status = 2
    engine.current_load_w = 1000.0  # Home load = 1000W
    engine.solar.instant_generation_power = 200.0  # Solar = 200W
    # Net Load = 1000 - 200 = 800W. 
    # Rated = 700W. So FC Gen should be min(700, 800) = 700.
    engine.update_simulation()
    
    assert engine.fuel_cell.instant_generation_power_w == 700, f"Expected 700, got {engine.fuel_cell.instant_generation_power_w}"
    print("Test 1 Passed: 逆潮流不可 (Net Load > Rated -> Gen = Rated)")
    
    engine.current_load_w = 400.0  # load = 400W
    engine.solar.instant_generation_power = 200.0  # Solar = 200W
    # Net load = 200W. 
    # Rated = 700W. FC Gen should be min(700, 200) = 200.
    engine.update_simulation()
    assert engine.fuel_cell.instant_generation_power_w == 200, f"Expected 200, got {engine.fuel_cell.instant_generation_power_w}"
    print("Test 2 Passed: 逆潮流不可 (Net Load < Rated -> Gen = Net Load)")
    
    engine.current_load_w = 100.0  # load = 100W
    engine.solar.instant_generation_power = 200.0  # Solar = 200W
    # Net load = -100W. Max(0, -100) = 0.
    # Gen should be 0.
    engine.update_simulation()
    assert engine.fuel_cell.instant_generation_power_w == 0, f"Expected 0, got {engine.fuel_cell.instant_generation_power_w}"
    print("Test 3 Passed: 逆潮流不可 (Net Load < 0 -> Gen = 0)")

    # 2. 逆潮流可能 (interconnection_status == 0)
    engine.fuel_cell.interconnection_status = 0
    engine.current_load_w = 100.0
    engine.solar.instant_generation_power = 200.0
    engine.update_simulation()
    assert engine.fuel_cell.instant_generation_power_w == 700, f"Expected 700, got {engine.fuel_cell.instant_generation_power_w}"
    print("Test 4 Passed: 逆潮流可能 (Gen = Rated)")
    
    # 3. Adapter Tests
    adapter = FuelCellAdapter(engine.fuel_cell)
    # Test 0xCA get
    res = adapter.get_property(0xCA)
    assert res == b'\x41', f"Expected 0x41, got {res}"
    print("Test 5 Passed: Adapter Get 0xCA")
    
    # Test 0xCA set
    adapter.set_property(0xCA, b'\x42')
    assert engine.fuel_cell.power_generation_setting == 0x42
    assert engine.fuel_cell.power_generation_status == 0x42
    print("Test 6 Passed: Adapter Set 0xCA")
    
    print("All Fuel Cell Tests Passed!")

if __name__ == "__main__":
    test_fuel_cell()
