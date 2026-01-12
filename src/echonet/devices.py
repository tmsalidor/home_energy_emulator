import struct

class ECHONETObject:
    """ECHONET Lite 機器オブジェクトのベースクラス"""
    def __init__(self, cls_code: int, ins_id: int):
        self.code = (cls_code, ins_id)
        self.properties = {} # EPC -> bytearray

    def set_property(self, epc: int, value: bytearray):
        self.properties[epc] = value

    def get_property(self, epc: int) -> bytearray:
        return self.properties.get(epc, bytearray())

    def process_request(self, data, addr):
        """受信フレーム（EHD以降）を受け取り、レスポンスを返す"""
        # ESVなどを解析して Get / Set に対応する
        tid = data[2] << 8 | data[3]
        seoj = data[4:7]
        deoj = data[7:10]
        esv = data[10]
        opc = data[11]
        
        # 簡易応答: Get (0x62) に対して Get_Res (0x72) を返す
        if esv == 0x62:
            self.handle_get(data, addr, tid, seoj, deoj)

    def handle_get(self, data, addr, tid, seoj, deoj):
        # TODO: 実際のUDP送信処理を stack 経由で呼び出す
        pass

class SmartMeter(ECHONETObject):
    """低圧スマートメーター (0x0288)"""
    def __init__(self, ins_id: int = 1):
        super().__init__(0x0288, ins_id)
        # 必須プロパティの初期化 (例)
        self.set_property(0x80, bytearray([0x30])) # 動作状態 (ON)
        self.set_property(0xD3, struct.pack(">I", 0)) # 係数
        self.set_property(0xE0, struct.pack(">i", 0)) # 積算電力量（正）
        self.set_property(0xE7, struct.pack(">i", 0)) # 瞬時電力

    def update_from_engine(self, ems_manager):
        """シミュレーションエンジンの値からプロパティを更新"""
        power = int(ems_manager.grid.power_w)
        self.set_property(0xE7, struct.pack(">i", power))

class SolarPower(ECHONETObject):
    """一般用太陽光発電 (0x0279)"""
    def __init__(self, ins_id: int = 1):
        super().__init__(0x0279, ins_id)
        self.set_property(0x80, bytearray([0x30])) # 動作状態 (ON)
        self.set_property(0xE0, struct.pack(">i", 0)) # 瞬時発電電力

    def update_from_engine(self, ems_manager):
        power = int(ems_manager.solar.power_w)
        self.set_property(0xE0, struct.pack(">i", power))

class Battery(ECHONETObject):
    """住宅用蓄電池 (0x027D)"""
    def __init__(self, ins_id: int = 1):
        super().__init__(0x027D, ins_id)
        self.set_property(0x80, bytearray([0x30])) # 動作状態 (ON)
        self.set_property(0xCF, bytearray([0x40])) # 運転モード (その他想定)
        self.set_property(0xD3, struct.pack(">B", 0)) # SOC (%)
        self.set_property(0xE0, struct.pack(">i", 0)) # 瞬時充放電電力 (正: 充電, 負: 放電)

    def update_from_engine(self, ems_manager):
        power = int(ems_manager.battery.power_w)
        soc = int(ems_manager.battery.soc_percent)
        self.set_property(0xE0, struct.pack(">i", power))
        self.set_property(0xD3, struct.pack(">B", soc))
        # 積算電力の計算・反映ロジックも追加予定
