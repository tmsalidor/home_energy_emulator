# Power Distribution Board Metering (分電盤メータリング) Default Properties
# ECHONET Lite Class: 0x0287
#
# チャンネルマッピング:
#   主幹: スマートメーター (売電/買電)
#   CH1: エコキュート (電気温水器)
#   CH2: エアコン
#   CH3-CH8: 未使用 (常にゼロ)
#   CH9-CH15: 存在しない (B1=8)

USER_JSON_DISTRIBUTION_BOARD = [
    {"epc": 0x80, "edt": [0x30]},                                                                                      # Operation Status: ON
    {"epc": 0x81, "edt": [0xFF]},                                                                                      # Installation Location
    {"epc": 0x82, "edt": [0x00, 0x00, 0x4A, 0x00]},                                                                   # Standard Version Information
    {"epc": 0x83, "edt": [0xFE, 0x00, 0x00, 0x0B, 0x00, 0x00, 0x02, 0x87, 0x01, 0x00, 0xC0, 0x8F, 0xFF, 0xFE, 0x73, 0xCE, 0x69]},  # Identification Number
    {"epc": 0x86, "edt": [0x0A, 0x00, 0x00, 0x0B, 0x01, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},       # Manufacturer's Fault Code
    {"epc": 0x88, "edt": [0x42]},                                                                                      # Fault Status: No Fault
    {"epc": 0x89, "edt": [0x00, 0x00]},                                                                               # Fault Description
    {"epc": 0x8A, "edt": [0x00, 0x00, 0x0B]},                                                                         # Manufacturer Code
    {"epc": 0x8C, "edt": [0x4D, 0x4B, 0x4E, 0x37, 0x33, 0x35, 0x30, 0x53, 0x31, 0x00, 0x00, 0x00]},                 # Product Code: "MKN7350S1"
    {"epc": 0x97, "edt": [0x0E, 0x27]},                                                                               # Current Time Setting
    {"epc": 0x98, "edt": [0x07, 0xE6, 0x05, 0x13]},                                                                   # Current Date Setting
    {"epc": 0x9D, "edt": [0x05, 0x80, 0x81, 0x86, 0x88, 0x89]},                                                      # Status Change Announcement Property Map
    {"epc": 0x9E, "edt": [0x0B, 0x81, 0x97, 0x98, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF9]},                # Set Property Map
    # 0x9F (Get Property Map) は静的テーブルから除外 → アダプターで _get_supported_epcs() から動的構築
    {"epc": 0xB0, "edt": [0x00]},                                                                                      # Master rated capacity
    {"epc": 0xB1, "edt": [0x08]},                                                                                      # Number of measurement channels (simplex): 8
    {"epc": 0xB2, "edt": [0x01, 0x08]},                                                                               # Channel range spec (simplex cumulative): ch1-8
    # 0xB3 (積算電力量リスト) は静的テーブルから除外 → アダプターで動的構築
    {"epc": 0xB6, "edt": [0x01, 0x08]},                                                                               # Channel range spec (simplex instant power): ch1-8
    # 0xB7 (瞬時電力リスト) は静的テーブルから除外 → アダプターで動的構築
    {"epc": 0xB8, "edt": [0xFD]},                                                                                      # Number of measurement channels (duplex): N/A
    {"epc": 0xB9, "edt": [0xFD, 0xFD]},                                                                               # Channel range spec (duplex cumulative): N/A
    {"epc": 0xBA, "edt": [0xFD, 0xFD]},                                                                               # Measured cumulative list (duplex): N/A
    {"epc": 0xBD, "edt": [0xFD, 0xFD]},                                                                               # Channel range spec (duplex instant power): N/A
    {"epc": 0xBE, "edt": [0xFD, 0xFD]},                                                                               # Measured instant amount list (duplex): N/A
    # 0xC0 (主幹積算正方向) は静的テーブルから除外 → アダプターで動的応答 (スマートメーター買電)
    # 0xC1 (主幹積算逆方向) は静的テーブルから除外 → アダプターで動的応答 (スマートメーター売電)
    {"epc": 0xC2, "edt": [0x02]},                                                                                      # Unit for cumulative energy: 0x02 = 0.01kWh
    # 0xC6 (主幹瞬時電力) は静的テーブルから除外 → アダプターで動的応答 (スマートメーター瞬時電力)
    # 0xC7 (主幹瞬時電流) は静的テーブルから除外 → アダプターで動的応答
    {"epc": 0xC8, "edt": [0x04, 0x11, 0x04, 0x0E]},                                                                   # Measured instantaneous voltage (static)
    # --- Per-channel cumulative data (8 bytes each: 4B normal + 4B reverse) ---
    # CH1-CH8 のみ。動的値はアダプターでオーバーライド。
    {"epc": 0xD0, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch1 (動的: エコキュート)
    {"epc": 0xD1, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch2 (動的: エアコン)
    {"epc": 0xD2, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch3 (未使用)
    {"epc": 0xD3, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch4 (未使用)
    {"epc": 0xD4, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch5 (未使用)
    {"epc": 0xD5, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch6 (未使用)
    {"epc": 0xD6, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch7 (未使用)
    {"epc": 0xD7, "edt": [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                                           # ch8 (未使用)
    # CH9-CH19 (0xD8-0xE2) は削除済み — B1=8 のため存在しない
]

DISTRIBUTION_BOARD_STATIC_PROPS: dict[int, bytes] = {}
for item in USER_JSON_DISTRIBUTION_BOARD:
    epc = item['epc']
    DISTRIBUTION_BOARD_STATIC_PROPS[epc] = bytes(item['edt'])
