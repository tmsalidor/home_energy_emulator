"""V2H 放電バグ修正後の動作確認スクリプト"""
import sys
sys.path.insert(0, 'src')

from src.core.engine import engine

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

print("=== V2H 放電バグ修正 確認テスト ===\n")

# --- シナリオ1: ソーラー > Load のとき放電しても売電が増えない ---
print("[シナリオ1] Solar 3000W, Load 1000W -> V2H放電しても売電増加なし")
engine.use_scenario = False
engine.current_load_w = 1000.0
engine.solar.instant_generation_power = 3000.0
engine.battery.is_charging = False
engine.battery.is_discharging = False
engine.water_heater.is_heating = False

# V2Hを放電モードに設定
engine.v2h.vehicle_connected = True
engine.air_conditioner.is_running = False
engine.v2h.operation_mode = 0x43
engine.v2h.remaining_capacity_wh = 25000.0
engine.v2h.charge_power_w = 3000.0
engine.v2h.discharge_power_w = 3000.0

engine.update_simulation()
grid_with_v2h = engine.smart_meter.instant_current_power
v2h_discharge = engine.v2h.current_discharge_w

# Solar 3000W > Load 1000W -> net_grid = 1000 - 3000 = -2000W (既に売電)
# V2H は net_grid > 50 でないので放電すべきでない
check("V2H放電量 (solar>load のとき放電0)", v2h_discharge, 0.0)
check("Grid (1000-3000=-2000W)", grid_with_v2h, -2000.0, tolerance=5.0)

print()

# --- シナリオ2: Load > Solar + 50W のとき放電する ---
print("[シナリオ2] Solar 1000W, Load 2000W -> V2H放電が発生してグリッド削減")
engine.current_load_w = 2000.0
engine.solar.instant_generation_power = 1000.0
engine.v2h.vehicle_connected = True
engine.v2h.operation_mode = 0x43
engine.v2h.remaining_capacity_wh = 25000.0
engine.v2h.discharge_power_w = 3000.0

engine.update_simulation()
grid_with_v2h = engine.smart_meter.instant_current_power
v2h_discharge = engine.v2h.current_discharge_w

# net_grid = 2000 - 1000 = 1000W, over_50 = 950W, discharge = min(950, 3000) = 950W
# p_grid = (2000) - (1000 + 950) = 50W
check("V2H放電量 (over_50=950W, min(950,3000)=950W)", v2h_discharge, 950.0, tolerance=1.0)
check("Grid after V2H discharge (~50W)", grid_with_v2h, 50.0, tolerance=5.0)

print()

# --- シナリオ3: Load < 50W のとき放電しない ---
print("[シナリオ3] Solar 0W, Load 30W -> V2H放電しない")
engine.current_load_w = 30.0
engine.solar.instant_generation_power = 0.0
engine.v2h.vehicle_connected = True
engine.v2h.operation_mode = 0x43

engine.update_simulation()
v2h_discharge = engine.v2h.current_discharge_w
check("V2H放電量 (load<50W のとき放電0)", v2h_discharge, 0.0)

print()

# --- シナリオ4: V2H充電時はgridに充電分が加算される ---
print("[シナリオ4] Solar 0W, Load 500W, V2H充電3000W")
engine.current_load_w = 500.0
engine.solar.instant_generation_power = 0.0
engine.v2h.vehicle_connected = True
engine.v2h.operation_mode = 0x42
engine.v2h.charge_power_w = 3000.0
engine.v2h.remaining_capacity_wh = 5000.0

engine.update_simulation()
grid_with_v2h = engine.smart_meter.instant_current_power
v2h_charge = engine.v2h.current_charge_w

check("V2H充電量 (3000W)", v2h_charge, 3000.0, tolerance=1.0)
check("Grid = 500 + 3000 = 3500W", grid_with_v2h, 3500.0, tolerance=5.0)

print()

# --- シナリオ5: 放電中に売電が発生しないことを確認 ---
print("[シナリオ5] Solar 500W, Load 2000W, V2H放電 -> Gridが負にならない")
engine.current_load_w = 2000.0
engine.solar.instant_generation_power = 500.0
engine.v2h.vehicle_connected = True
engine.v2h.operation_mode = 0x43
engine.v2h.discharge_power_w = 5000.0  # 大きな放電電力
engine.v2h.remaining_capacity_wh = 25000.0

engine.update_simulation()
grid_with_v2h = engine.smart_meter.instant_current_power
v2h_discharge = engine.v2h.current_discharge_w

# net_grid = 2000 - 500 = 1500W, over_50 = 1450W, discharge = min(1450, 5000) = 1450W
# p_grid = 2000 - (500 + 1450) = 50W
check("Grid >= 0 (売電なし)", grid_with_v2h >= 0, True)
check("Grid ~= 50W (50W分だけ買電)", grid_with_v2h, 50.0, tolerance=5.0)

print(f"\n=== 結果: {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
