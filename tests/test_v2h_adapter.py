"""V2HAdapter の動作確認スクリプト"""
import sys
import struct
sys.path.insert(0, 'src')

from src.core.engine import engine
from src.core.adapters import V2HAdapter

adapter = V2HAdapter(engine.v2h)
passed = 0
failed = 0

def check(label, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  [OK] {label}: {actual}")
        passed += 1
    else:
        print(f"  [NG] {label}: got {actual}, expected {expected}")
        failed += 1

print("=== V2H Adapter Tests ===")

# 初期状態チェック
r = adapter.get_property(0xC7)
check("C7 initial (disconnected)", r.hex(), "30")

r = adapter.get_property(0xDA)
check("DA initial (stop)", r.hex(), "47")

r = adapter.get_property(0xE1)
check("E1 initial (stop)", r.hex(), "47")

# D3 初期（停止）
r = adapter.get_property(0xD3)
check("D3 initial (0W)", struct.unpack(">i", r)[0], 0)

# 未接続時のDA Set -> 失敗
ok = adapter.set_property(0xDA, b'\x42')
check("SET DA=42 disconnected -> False", ok, False)

# CD Set: 接続
adapter.set_property(0xCD, b'\x00')
r = adapter.get_property(0xC7)
check("C7 after connect (0x43)", r.hex(), "43")

r = adapter.get_property(0xDA)
check("DA after connect (standby 0x44)", r.hex(), "44")

# DA Set: 充電
ok = adapter.set_property(0xDA, b'\x42')
check("SET DA=42 (charge) -> True", ok, True)

r = adapter.get_property(0xDA)
check("DA after SET=42", r.hex(), "42")

r = adapter.get_property(0xE1)
check("E1 after mode=charge (42)", r.hex(), "42")

r = adapter.get_property(0xD3)
check("D3 charging (+3000W)", struct.unpack(">i", r)[0], 3000)

# DA Set: 放電
ok = adapter.set_property(0xDA, b'\x43')
check("SET DA=43 (discharge) -> True", ok, True)

r = adapter.get_property(0xE1)
check("E1 after mode=discharge (43)", r.hex(), "43")

r = adapter.get_property(0xD3)
check("D3 discharging (-3000W)", struct.unpack(">i", r)[0], -3000)

# DA Set: 待機
ok = adapter.set_property(0xDA, b'\x44')
check("SET DA=44 (standby) -> True", ok, True)

r = adapter.get_property(0xE1)
check("E1 after mode=standby (44)", r.hex(), "44")

# 無効なDA値
ok = adapter.set_property(0xDA, b'\x47')
check("SET DA=47 (invalid) -> False", ok, False)

# CD Set: 切断
adapter.set_property(0xCD, b'\x00')
r = adapter.get_property(0xC7)
check("C7 after disconnect (0x30)", r.hex(), "30")

r = adapter.get_property(0xDA)
check("DA after disconnect (stop 47)", r.hex(), "47")

# C0, C2 の確認
r = adapter.get_property(0xC0)
cap = struct.unpack(">L", r)[0]
check("C0 capacity (20000Wh)", cap, 20000)

r = adapter.get_property(0xC2)
remain = struct.unpack(">L", r)[0]
check("C2 remaining (10000Wh = 50%)", remain, 10000)

# EB, EC の確認
r = adapter.get_property(0xEB)
check("EB charge_power (3000W)", struct.unpack(">L", r)[0], 3000)

r = adapter.get_property(0xEC)
check("EC discharge_power (3000W)", struct.unpack(">L", r)[0], 3000)

print(f"\n=== Result: {passed} passed, {failed} failed ===")
sys.exit(0 if failed == 0 else 1)
