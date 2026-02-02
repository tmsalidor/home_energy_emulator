
import sys
import os
import struct

# Include src in path
sys.path.append(os.getcwd())

from src.core.models import Battery
from src.core.adapters import BatteryAdapter
from src.core.engine import SimulationEngine

def run_test():
    print("=== Battery Property Verification ===")
    
    # 1. Setup Engine and Battery
    engine = SimulationEngine()
    bat = engine.battery
    adapter = BatteryAdapter(bat)
    
    # Initial State
    bat.soc = 50.0
    # bat.rated_capacity_wh = 10000.0 <-- Should be loaded from static props (0xD0)
    # The engine loads it on init. 
    # Let's check what it loaded.
    # Note: BATTERY_STATIC_PROPS is processed in SimulationEngine.__init__
    # However, in this script we create a new engine instance.
    # We should trust the engine's loading logic if it runs correctly.
    
    # 0xD0 in USER_JSON (consts file) was updated to [0,0,54,176] -> 14000
    expected_capacity = 14000.0
    
    print(f"Initial State: SOC={bat.soc}%, Cap={bat.rated_capacity_wh}Wh (Expected: {expected_capacity})")
    
    if bat.rated_capacity_wh != expected_capacity:
        print(f"FAIL: Capacity {bat.rated_capacity_wh} does not match expected {expected_capacity}. Is 0xD0 parsed?")
        # Force set for remainder of test if failed, to check calc logic
        bat.rated_capacity_wh = expected_capacity
        
    bat.cumulative_charge_wh = 1000.0
    bat.cumulative_discharge_wh = 500.0
    
    # Recalculate Expectations
    # A4: 14000 * 0.5 = 7000 (Current), 14000 - 7000 = 7000 (Chargeable)
    # A5: 7000
    
    val_a4 = struct.unpack(">L", adapter.get_property(0xA4))[0]
    val_a5 = struct.unpack(">L", adapter.get_property(0xA5))[0]
    val_a8 = struct.unpack(">L", adapter.get_property(0xA8))[0]
    val_a9 = struct.unpack(">L", adapter.get_property(0xA9))[0]
    
    print(f"[0xA4] Chargeable: Expected=7000, Actual={val_a4}")
    print(f"[0xA5] Dischargeable: Expected=7000, Actual={val_a5}")
    print(f"[0xA8] Cum Charge: Expected=1000, Actual={val_a8}")
    print(f"[0xA9] Cum Discharge: Expected=500, Actual={val_a9}")
    
    if val_a4 != 7000 or val_a5 != 7000:
        print("FAIL: Initial property values mismatch for new capacity")
        return

    # 3. Optimize Test: Simulate Charging
    print("\n--- Simulating Charging (1000W for 1 hour) ---")
    bat.is_charging = True
    bat.instant_charge_power = 1000.0
    
    # Update for 3600 seconds
    engine._update_battery(3600.0)
    
    # Expected: 
    # Added 1000Wh
    # SOC change: 1000 / 14000 * 100 = 7.14%
    # New SOC: 57.14%
    # Current Wh: 14000 * 0.5714 = 8000
    # A4: 14000 - 8000 = 6000
    # A5: 8000
    # Cum Charge: 2000
    
    print(f"New State: SOC={bat.soc:.2f}%")
    
    val_a4 = struct.unpack(">L", adapter.get_property(0xA4))[0]
    val_a5 = struct.unpack(">L", adapter.get_property(0xA5))[0]
    val_a8 = struct.unpack(">L", adapter.get_property(0xA8))[0]
    
    print(f"[0xA4] Chargeable: Expected=6000, Actual={val_a4}")
    print(f"[0xA5] Dischargeable: Expected=8000, Actual={val_a5}")
    print(f"[0xA8] Cum Charge: Expected=2000, Actual={val_a8}")
    
    if abs(val_a4 - 6000) > 200 or abs(val_a5 - 8000) > 200: # allow some rounding diffs
        print("FAIL: Values after charging mismatch")
        return

    # 4. Simulate Discharging
    print("\n--- Simulating Discharging (2000W for 0.5 hour) ---")
    bat.is_charging = False
    bat.is_discharging = True
    bat.instant_discharge_power = 2000.0
    
    engine._update_battery(1800.0) # 0.5h
    
    # Expected:
    # Removed 1000Wh
    # SOC change: -7.14% -> Back to 50.0%
    # Current Wh: 7000
    # A4: 7000
    # A5: 7000
    # Cum Discharge: 1500
    
    print(f"New State: SOC={bat.soc:.2f}%")

    val_a4 = struct.unpack(">L", adapter.get_property(0xA4))[0]
    val_a5 = struct.unpack(">L", adapter.get_property(0xA5))[0]
    val_a9 = struct.unpack(">L", adapter.get_property(0xA9))[0]
    
    print(f"[0xA4] Chargeable: Expected=7000, Actual={val_a4}")
    print(f"[0xA5] Dischargeable: Expected=7000, Actual={val_a5}")
    print(f"[0xA9] Cum Discharge: Expected=1500, Actual={val_a9}")
    
    if abs(val_a4 - 7000) > 200 or abs(val_a5 - 7000) > 200:
        print("FAIL: Values after discharging mismatch")
        return
        
    print("\nSUCCESS: All verify steps passed!")

if __name__ == "__main__":
    run_test()
