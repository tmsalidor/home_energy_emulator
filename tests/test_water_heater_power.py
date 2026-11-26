"""電気給湯器 (エコキュート) の瞬時消費電力 (0x84)・積算消費電力量 (0x85) の動作確認テスト"""
import sys
import struct
sys.path.insert(0, 'src')

from src.config.settings import settings
from src.core.engine import engine
from src.core.adapters import ElectricWaterHeaterAdapter
from src.core.water_heater_consts import WATER_HEATER_STATIC_PROPS

wh = engine.water_heater
adapter = ElectricWaterHeaterAdapter(wh)
passed = 0
failed = 0


def check(label, actual, expected):
    global passed, failed
    ok = actual == expected
    status = "[OK]" if ok else "[NG]"
    print(f"  {status} {label}: {actual}" + (f" (expected {expected})" if not ok else ""))
    if ok:
        passed += 1
    else:
        failed += 1


def get_u16(epc):
    return struct.unpack(">H", adapter.get_property(epc))[0]


def get_u32(epc):
    return struct.unpack(">L", adapter.get_property(epc))[0]


def get_map_epcs():
    data = adapter.get_property(0x9F)
    count, bitmap = data[0], data[1:]
    # ECHONET Lite の記述形式 2: n バイト目の bit b が EPC 0x80 + 0x10 * b + n
    epcs = [0x80 + 0x10 * b + n for n, byte in enumerate(bitmap) for b in range(8) if byte & (1 << b)]
    return count, sorted(epcs)


base_wh = struct.unpack(">L", WATER_HEATER_STATIC_PROPS[0x85])[0]

print("=== 電気給湯器 0x84 / 0x85 テスト ===\n")
engine.use_scenario = False
settings.echonet.water_heater_instant_power = True
wh.is_running = True
wh.cumulative_power_wh = 0.0
wh.heating_power_w = 1200.0

print("--- 沸き上げていないとき ---")
wh.auto_setting = 0x41
wh.is_heating = False
check("0x84 は 0 W", get_u16(0x84), 0)
check("0x85 は静的テーブルの値", get_u32(0x85), base_wh)

print("\n--- 手動沸き上げ (0xB0 = 0x42) で 1 時間 ---")
adapter.set_property(0xB0, b'\x42')
wh.remaining_hot_water = 0.0
wh.tank_capacity = 1000  # 1 時間では満タンにしない
for _ in range(3600):
    engine._update_water_heater(1.0)
check("0xB2 は沸き上げ中", adapter.get_property(0xB2), b'\x41')
check("0x84 は heating_power_w", get_u16(0x84), 1200)
check("0x85 は 1200 Wh 増える", get_u32(0x85) - base_wh, 1200)

print("\n--- 手動沸き上げ停止 (0xB0 = 0x43) ---")
adapter.set_property(0xB0, b'\x43')
engine._update_water_heater(60.0)
check("0x84 は 0 W に戻る", get_u16(0x84), 0)
check("0x85 は増えない", get_u32(0x85) - base_wh, 1200)

print("\n--- 運転停止 (0x80 = 0x31) 中は沸き上げ中でも 0 W ---")
wh.is_heating = True
wh.is_running = False
check("0x84 は 0 W", get_u16(0x84), 0)
wh.is_running = True
wh.is_heating = False

print("\n--- Get プロパティマップ (0x9F) ---")
count, epcs = get_map_epcs()
check("0x84 が入る", 0x84 in epcs, True)
check("0x85 が入る", 0x85 in epcs, True)
check("件数とビットの数が合う", count, len(epcs))

# 静的テーブルの 0x9F に 0x84 (4 バイト目の bit 0) を足したものと同じ
expected = bytearray(WATER_HEATER_STATIC_PROPS[0x9F])
expected[0] += 1
expected[1 + 4] |= 0x01
check("静的テーブルの 0x9F に 0x84 を足したものと同じ", adapter.get_property(0x9F), bytes(expected))

print("\n--- 0x84 を持たない機種として動かす (water_heater_instant_power = False) ---")
settings.echonet.water_heater_instant_power = False
check("0x84 に応答しない", adapter.get_property(0x84), None)
count, epcs = get_map_epcs()
check("0x9F に 0x84 が入らない", 0x84 in epcs, False)
check("0x9F に 0x85 は入る", 0x85 in epcs, True)
check("件数とビットの数が合う", count, len(epcs))
check("静的テーブルの 0x9F と同じ", adapter.get_property(0x9F), WATER_HEATER_STATIC_PROPS[0x9F])
settings.echonet.water_heater_instant_power = True

print(f"\n結果: {passed} OK / {failed} NG")
sys.exit(1 if failed else 0)
