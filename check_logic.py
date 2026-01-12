import struct

# 1. 簡易的な DeviceState と EMSManager (src/core/ems_manager.py より再掲)
class DeviceState:
    def __init__(self):
        self.power_w = 0.0

class EMSManager:
    def __init__(self):
        self.grid = DeviceState()
        self.load = DeviceState()
        self.solar = DeviceState()
        self.battery = DeviceState()

    def update_balance(self):
        self.grid.power_w = (self.load.power_w + self.battery.power_w) - self.solar.power_w

# 2. テスト実行
def run_test():
    ems = EMSManager()
    
    # ケース1: 負荷1000W, 太陽光400W, 蓄電池200W(充電) -> グリッド800W
    ems.load.power_w = 1000
    ems.solar.power_w = 400
    ems.battery.power_w = 200
    ems.update_balance()
    print(f"Test 1 (Grid): {ems.grid.power_w} W (Expected: 800.0)")
    assert ems.grid.power_w == 800.0

    # ケース2: ECHONET Lite プロパティ形式 (i)
    power_int = int(ems.grid.power_w)
    packed = struct.pack(">i", power_int)
    unpacked = struct.unpack(">i", packed)[0]
    print(f"Test 2 (Packed Power): {unpacked} (Expected: 800)")
    assert unpacked == 800

    print("--- Logic Check PASSED ---")

if __name__ == "__main__":
    run_test()
