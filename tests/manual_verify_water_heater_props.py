
import sys
import os
import struct

# Include src in path
sys.path.append(os.getcwd())

from src.core.models import ElectricWaterHeater
from src.core.adapters import ElectricWaterHeaterAdapter
from src.core.engine import SimulationEngine

def run_test():
    print("=== Electric Water Heater Property Verification ===")
    
    # 1. Setup Engine and Device
    engine = SimulationEngine()
    wh = engine.water_heater
    adapter = ElectricWaterHeaterAdapter(wh)
    
    # 2. Verify Initial State
    # Expected Defaults: E3=0x42 (Manual Stop/Off), C0=0x42 (Off/Standby)
    # Check what we set in models.py
    # e3_bath_operation_status = 0x42
    # c0_operation_status = 0x42
    
    print("\n--- Checking Initial Values ---")
    val_e3 = adapter.get_property(0xE3)
    val_c0 = adapter.get_property(0xC0)
    
    print(f"[0xE3] Initial: {val_e3.hex().upper()} (Expected: 42)")
    print(f"[0xC0] Initial: {val_c0.hex().upper()} (Expected: 42)")
    
    if val_e3 != b'\x42' or val_c0 != b'\x42':
        print("FAIL: Initial values do not match expected defaults.")
        return

    # 3. Test Set & Get 0xE3
    print("\n--- Testing 0xE3 (Bath Operation Status) ---")
    # Set to 0x41 (Auto)
    success = adapter.set_property(0xE3, b'\x41')
    print(f"Set 0xE3 to 0x41: Success={success}")
    
    val_e3_new = adapter.get_property(0xE3)
    print(f"Get 0xE3: {val_e3_new.hex().upper()} (Expected: 41)")
    
    if val_e3_new != b'\x41':
        print("FAIL: 0xE3 did not update correctly.")
        return

    # 4. Test Set & Get 0xC0
    print("\n--- Testing 0xC0 (Operation Status) ---")
    # Set to 0x41 (On?)
    success = adapter.set_property(0xC0, b'\x41')
    print(f"Set 0xC0 to 0x41: Success={success}")
    
    val_c0_new = adapter.get_property(0xC0)
    print(f"Get 0xC0: {val_c0_new.hex().upper()} (Expected: 41)")
    
    if val_c0_new != b'\x41':
        print("FAIL: 0xC0 did not update correctly.")
        return

    # 5. Verify Persistence in Model
    print("\n--- Verifying Model Persistence ---")
    print(f"Model E3: {wh.e3_bath_operation_status} (0x{wh.e3_bath_operation_status:02X})")
    print(f"Model C0: {wh.c0_operation_status} (0x{wh.c0_operation_status:02X})")
    
    if wh.e3_bath_operation_status != 0x41 or wh.c0_operation_status != 0x41:
        print("FAIL: Model values not updated.")
        return

    print("\nSUCCESS: All verify steps passed!")

if __name__ == "__main__":
    run_test()
