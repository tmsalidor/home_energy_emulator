# User provided Smart Meter Properties
# EPC (Decimal) -> EDT (List of Decimals)
# Converted to EPC (Hex int) -> Bytes



# Full raw data from user request for exactness
USER_JSON = [
    {"epc":128,"edt":[48]},
    {"epc":224,"edt":[0,0,0,0]},
    {"epc":129,"edt":[1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]},
    {"epc":225,"edt":[0]},
    {"epc":130,"edt":[0,0,70,0]},
    {"epc":226,"edt":[0] * 194},
    {"epc":131,"edt":[254,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]},
    {"epc":147,"edt":[145]},
    {"epc":211,"edt":[0,0,0,0]},
    {"epc":227,"edt":[0,0,0,0]},
    {"epc":132,"edt":[0,0]},
    {"epc":228,"edt":[0] * 194},
    {"epc":133,"edt":[0,0,0,0]},
    {"epc":229,"edt":[0]},
    {"epc":134,"edt":[0,0,0,0]},
    {"epc":135,"edt":[100]},
    {"epc":151,"edt":[14,59]},
    {"epc":215,"edt":[1]}, # 0xD7
    {"epc":231,"edt":[0,0,0,100]}, # 0xE7
    {"epc":136,"edt":[66]},
    {"epc":152,"edt":[7,231,8,24]},
    {"epc":232,"edt":[0,0,0,0]},
    {"epc":137,"edt":[0,0]},
    {"epc":153,"edt":[0,0]},
    {"epc":138,"edt":[0,0,0]},
    {"epc":154,"edt":[67,0,0,0,0]},
    {"epc":234,"edt":[7,231,8,24,14,59,11,0,1,108,255]},
    {"epc":139,"edt":[0,0,0]},
    {"epc":235,"edt":[7,231,8,24,14,59,12,0,1,83,108]},
    {"epc":140,"edt":[48,48,48,48,48,48,48,48,48,48,48,48]},
    {"epc":236,"edt":[7,231,8,24,14,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]},
    {"epc":141,"edt":[48,48,48,48,48,48,48,48,48,48,48,48]},
    {"epc":157,"edt":[3,128,129,136]},
    {"epc":237,"edt":[7,231,8,24,14,0,1]},
    {"epc":142,"edt":[7,222,7,1]},
    {"epc":158,"edt":[10,128,129,135,143,147,151,152,153,229,237]},
    {"epc":143,"edt":[66]},
    {"epc":159,"edt":[38,65,65,65,99,65,65,1,99,67,3,67,65,65,67,3,3]}
]

# Convert to Dictionary {EPC(int): bytes}
# Skip 0x9D(157), 0x9E(158), 0x9F(159) as they are map properties handled dynamically
SMART_METER_STATIC_PROPS = {}
for item in USER_JSON:
    epc = item['epc']
    # if epc in [157, 158, 159]: continue # Maps - User provided data should be used as is
    SMART_METER_STATIC_PROPS[epc] = bytes(item['edt'])
