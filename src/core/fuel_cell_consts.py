# Fuel Cell (燃料電池) Default Properties
# ECHONET Lite Class: 0x027C

USER_JSON_FUEL_CELL = [
    {"epc": 0x80, "edt": [0x30]},                                                                                      # Operation Status: ON
    {"epc": 0xD0, "edt": [0x02]},                                                                                      # System interconnection status: 0x02=independent
    {"epc": 0x81, "edt": [0x00]},                                                                                      # Installation Location
    {"epc": 0xD1, "edt": [0xFF, 0xFF, 0xFF, 0xFF]},                                                                   # Power generation request time setting
    {"epc": 0xE1, "edt": [0x00, 0x00]},                                                                               # (0xE1)
    {"epc": 0x82, "edt": [0x00, 0x00, 0x4A, 0x00]},                                                                   # Standard Version Information
    {"epc": 0xC2, "edt": [0x02, 0xBC]},                                                                               # Rated power generation output: 0x02BC = 700W
    {"epc": 0xD2, "edt": [0x42]},                                                                                      # Designated power generation status
    {"epc": 0xE2, "edt": [0x00, 0x19]},                                                                               # (0xE2)
    {"epc": 0x83, "edt": [0xFE, 0x00, 0x00, 0x59, 0x02, 0x7C, 0x01, 0x00, 0x00, 0x00, 0x00, 0x2C, 0x4C, 0xC6, 0x5A, 0x1B, 0x06]},  # Identification Number
    {"epc": 0xC4, "edt": [0x02, 0xBC]},                                                                               # Measured instantaneous power generation output
    {"epc": 0xC5, "edt": [0x00, 0x00, 0x00, 0x00]},                                                                   # Measured cumulative amount of power generation: 0Wh
    {"epc": 0x86, "edt": [0x08, 0x00, 0x00, 0x59, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30, 0x30]},                 # (0x86)
    {"epc": 0xC7, "edt": [0x00, 0x00]},                                                                               # (0xC7)
    {"epc": 0x88, "edt": [0x42]},                                                                                      # Fault Status: No Fault
    {"epc": 0xC8, "edt": [0x00, 0x00, 0x00, 0x00]},                                                                   # Measured cumulative gas consumption
    {"epc": 0x8A, "edt": [0x00, 0x00, 0x59]},                                                                         # Manufacturer Code
    {"epc": 0xCB, "edt": [0x42]},                                                                                      # Power generation status: 0x42=stopped
    {"epc": 0x8C, "edt": [0x41, 0x49, 0x53, 0x49, 0x4E, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]},                 # Product Code: "AISIN"
    {"epc": 0xCC, "edt": [0x03, 0xE8]},                                                                               # (0xCC)
    {"epc": 0x9D, "edt": [0x05, 0x80, 0x81, 0x86, 0x88, 0xCB]},                                                      # Status Change Announcement Property Map
    {"epc": 0xCD, "edt": [0x00, 0x00, 0x00, 0x00]},                                                                   # Measured in-house cumulative power consumption
    {"epc": 0x9E, "edt": [0x03, 0x81, 0xD1, 0xD2]},                                                                  # Set Property Map
    {"epc": 0x9F, "edt": [0x18, 0x21, 0x61, 0x71, 0x01, 0x10, 0x10, 0x01, 0x10, 0x11, 0x00, 0x01, 0x10, 0x11, 0x12, 0x02, 0x02]},  # Get Property Map (24 EPCs)
]

FUEL_CELL_STATIC_PROPS: dict[int, bytes] = {}
for item in USER_JSON_FUEL_CELL:
    epc = item['epc']
    FUEL_CELL_STATIC_PROPS[epc] = bytes(item['edt'])
