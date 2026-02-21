"""V2H 0xD3計測値と放電制限の連動テスト"""
import sys
import struct
sys.path.insert(0, 'src')

from src.core.engine import engine
from src.core.adapters import V2HAdapter

adapter = V2HAdapter(engine.v2h)
passed = 0
failed = 0

def check(label, actual, expected, tolerance=None):
    global passed, failed
    if tolerance is not None:
        ok = abs(actual - expected) <= tolerance
    else:
        ok = actual == expected
    status = "[OK]" if ok else "[NG]"
    print(f"  {status} {label}: {actual}" + (f" (expected {expected})" if not ok else ""))
    if ok:
        passed += 1
    else:
        failed += 1

print("=== V2H 0xD3 実測値・制限連動テスト ===\n")

# 初期化
engine.use_scenario = False
engine.v2h.vehicle_connected = True
engine.v2h.operation_mode = 0x43 # 放電
engine.v2h.discharge_power_w = 3000.0
engine.v2h.remaining_capacity_wh = 25000.0

# シナリオ1: 低負荷 (300W) -> 放電量が 250W (Load 300 - 50 = 250) に制限される
print("[シナリオ1] Load 300W -> 放電制限 250W")
engine.current_load_w = 300.0
engine.solar.instant_generation_power = 0.0
engine.update_simulation()

r = adapter.get_property(0xD3)
val = struct.unpack(">i", r)[0]
# 期待値: -250W (現在の current_discharge_w が 250.0 になっているはず)
check("0xD3 計測値 (制限後)", val, -250)
check("Engine 実放電量(w)", engine.v2h.current_discharge_w, 250.0)

print()

# シナリオ2: 高負荷 (5000W) -> 放電量が設定値 (3000W) に制限される
print("[シナリオ2] Load 5000W -> 放電量 3000W (設定値上限)")
engine.current_load_w = 5000.0
engine.update_simulation()

r = adapter.get_property(0xD3)
val = struct.unpack(">i", r)[0]
check("0xD3 計測値 (設定値上限)", val, -3000)
check("Engine 実放電量(w)", engine.v2h.current_discharge_w, 3000.0)

print()

# シナリオ3: ソーラー過剰 (3000W) -> 放電 0
print("[シナリオ3] Solar 3000W, Load 1000W -> 放電 0 (売電回避)")
engine.current_load_w = 1000.0
engine.solar.instant_generation_power = 3000.0
engine.update_simulation()

r = adapter.get_property(0xD3)
val = struct.unpack(">i", r)[0]
check("0xD3 計測値 (放電0)", val, 0)
check("Engine 実放電量(w)", engine.v2h.current_discharge_w, 0.0)

print(f"\n=== 結果: {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
