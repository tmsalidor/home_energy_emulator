"""V2H 積算電力量 (0xD8, 0xD6) の動作確認テスト"""
import sys
import struct
import time
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

print("=== V2H 積算電力量 (0xD8, 0xD6) テスト ===\n")

# 初期化
engine.use_scenario = False
v2h = engine.v2h
v2h.vehicle_connected = True
v2h.cumulative_charge_wh = 0.0
v2h.cumulative_discharge_wh = 0.0
v2h.battery_capacity_wh = 50000.0
v2h.remaining_capacity_wh = 25000.0

# 1. 充電による積算
print("[テスト1] 充電による積算 (3000W x 10秒)")
v2h.operation_mode = 0x42 # 充電
v2h.charge_power_w = 3000.0
dt = 10.0 # 10秒
# engine._update_v2h を直接呼んでシミュレート
engine._update_v2h(dt)

# 期待される累積: 3000 * (10/3600) = 8.333... Wh
expected_wh = 3000.0 * (10.0 / 3600.0)
check("累積充電 Wh (Engine)", v2h.cumulative_charge_wh, expected_wh, tolerance=0.001)

# アダプター経由での取得 (0xD8)
r = adapter.get_property(0xD8)
val = struct.unpack(">L", r)[0]
check("0xD8 (Adapter)", val, int(expected_wh))

print()

# 2. 放電による積算
print("[テスト2] 放電による積算 (2000W x 15秒)")
v2h.operation_mode = 0x43 # 放電
v2h.discharge_power_w = 2000.0
# 放電を有効にするために Load を高く設定 (engine ロジック上 net_grid > 50 が必要)
engine.current_load_w = 5000.0
engine.solar.instant_generation_power = 0.0
dt = 15.0 # 15秒
engine._update_v2h(dt)

# 期待される累積: 2000 * (15/3600) = 8.333... Wh
expected_wh_d = 2000.0 * (15.0 / 3600.0)
check("累積放電 Wh (Engine)", v2h.cumulative_discharge_wh, expected_wh_d, tolerance=0.001)

# アダプター経由での取得 (0xD6)
r = adapter.get_property(0xD6)
val = struct.unpack(">L", r)[0]
check("0xD6 (Adapter)", val, int(expected_wh_d))

print(f"\n=== 結果: {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
