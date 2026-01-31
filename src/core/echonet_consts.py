# ECHONET Lite Property Name Mapping

# 共通プロパティ (Super Class / Common)
SUPER_CLASS_EPCS = {
    0x80: "Operation Status",
    0x81: "Installation Location",
    0x82: "Standard Version Information",
    0x83: "Identification Number",
    0x84: "Instantaneous Power Consumption",
    0x85: "Cumulative Power Consumption",
    0x86: "Manufacturer's Fault Code",
    0x87: "Current Limit Setting",
    0x88: "Fault Status",
    0x89: "Fault Content",
    0x8A: "Manufacturer Code",
    0x8B: "Business Facility Code",
    0x8C: "Product Code",
    0x8D: "Production Number",
    0x8E: "Production Date",
    0x8F: "Power-saving Operation Setting",
    0x93: "Remote Control Setting",
    0x97: "Current Time Setting",
    0x98: "Current Date Setting",
    0x99: "Power Limit Setting",
    0x9A: "Cumulative Operation Time",
    0x9D: "Status Change Announcement Property Map",
    0x9E: "Set Property Map",
    0x9F: "Get Property Map",
}

# クラス固有プロパティ (Class Specific)
# Key: (ClassGroup, ClassCode) -> Value: {EPC: Name}
CLASS_EPCS = {
    # Node Profile (0x0EF0)
    (0x0E, 0xF0): {
        0xD3: "Self-node Instances Total Number",
        0xD4: "Self-node Instances List",
        0xD5: "Instance List Notification",
        0xD6: "Self-node Instance List S",
        0xD7: "Self-node Class List S",
    },

    # Solar Power (0x0279)
    (0x02, 0x79): {
        # Settings
        0xA0: "Output Control Setting 1",
        0xA1: "Output Control Setting 2",
        0xB0: "Output Control Schedule",
        0xB1: "Next Access Date and Time",
        0xB2: "Type for Function to Control Purchase of Excess Electricity",
        0xB3: "Output Change Time Setting Value",
        0xB4: "Upper Limit Clip Setting Value",
        
        0xC0: "Operation Factor Setting Value",
        0xC1: "FIT Contract Type",
        0xC2: "Self-Communication Type",
        0xC3: "Capacity Approved by Equipment",
        0xC4: "Conversion Coefficient",
        0xD0: "System interconnection status",
        0xD1: "Output power restraint status",
        
        0xE0: "Measured Instantaneous Amount of Electricity Generated",
        0xE1: "Measured Cumulative Amount of Electric Energy Generated",
        0xE2: "Resetting Cumulative Amount of Electric Energy Generated",
        0xE3: "Measured Cumulative Amount of Electric Energy  Sold",
        0xE4: "Resetting Cumulative Amount of Electric Energy  Sold",
        0xE5: "Power generation output limit setting 1",
        0xE6: "Power generation output limit setting 2",
        0xE7: "Limit setting for the amount of electricity sold",
        0xE8: "Rated power generation output (System-interconnected)",
        0xE9: "Rated power generation output (Independent)",
    },

    # Storage Battery (0x027D)
    (0x02, 0x7D): {
        # Status / Mode
        0x80: "Operation Status",

        0xA0: "AC Effective Capacity (Charge)",
        0xA1: "AC Effective Capacity (Discharge)",
        0xA2: "AC Chargeable Capacity",
        0xA3: "AC Dischargeable Capacity",
        0xA4: "AC Chargeable Electric Energy",
        0xA5: "AC Dischargeable Electric Energy",
        0xA6: "AC Charge Upper Limit Setting",
        0xA7: "AC Discharge Lower Limit Setting",
        0xA8: "AC cumulative charging electric energy",
        0xA9: "AC cumulative discharging electric energy",
        0xAA: "AC charge amount target value",
        0xAB: "AC discharge amounttarget value",

        0xC1: "Charging Method",
        0xC2: "Discharging Method",
        0xC7: "AC rated electric energy",
        0xC8: "Min/Max Charging Electric Power",
        0xC9: "Min/Max Discharging Electric Power",
        0xCA: "Min/Max Charging Current",
        0xCB: "Min/Max Discharging Current",
        0xCC: "Re-interconnection Permission Setting",
        0xCD: "Operation Permission Setting",
        0xCE: "Independent Operation Permission Setting",
        0xCF: "Working Operation Status",
        
        0xD0: "Rated Electric Energy",
        0xD1: "Rated Capacity",
        0xD2: "Rated Voltage",
        0xD3: "Measured Instantaneous Charge/Discharge Power",
        0xD4: "Measured Instantaneous Charge/Discharge Current",
        0xD5: "Measured Instantaneous Charge/Discharge Voltage",
        0xD6: "Measured Cumulative Discharging Electric Energy",
        0xD7: "Measured Cumulative Discharging Electric Reset Setting",
        0xD8: "Measured Cumulative Charging Electric Energy",
        0xD9: "Measured Cumulative Charging Electric Energy Reset Setting",
        0xDA: "Operation Mode Setting",
        0xDB: "System Interconnection Status",
        0xDC: "Minimum/maximum charging electric power (Independent)",
        0xDD: "Minimum/maximum discharging electric power (Independent)",
        0xDE: "Minimum/maximum charging current (Independent)",
        0xDF: "Minimum/maximum discharging current (Independent)",

        0xE0: "Charging/discharging amount setting 1",
        0xE1: "Charging/discharging amount setting 2",
        
        # Ratings / SOC
        0xE2: "Remaining stored electricity 1",
        0xE3: "Remaining stored electricity 2",
        0xE4: "Remaining stored electricity 3",
        0xE5: "Battery state of health",
        0xE6: "Battery type",
        0xE7: "Charging amount setting 1",
        0xE8: "Discharging amount setting 1",
        0xE9: "Charging amount setting 2",
        0xEA: "Discharging amount setting 2",
        0xEB: "Charging electric power setting",
        0xEC: "Discharging electric power setting",
        0xED: "Charging current setting",
        0xEE: "Discharging current setting",
        0xEF: "Rated voltage (Independent)",
    },

    # Smart Meter (0x0288)
    (0x02, 0x88): {
        0xC0: "Route B Identificati on number",
        0xD0: "Oneminute measured cumulative amounts of electric energy measured (normal and reverse directions)",
        0xD3: "Coefficient",
        0xD7: "Number of Effective Digits s for cumulative amount of electric energy",
        0xE0: "Measured Cumulative Amount of Electric Energy (Normal)",
        0xE1: "Unit for Cumulative Amounts of Electric Energy (Normal and Reverse)",
        0xE2: "Historical Data of Measured Cumulative Amount of Electric Energy 1 (Normal)",
        0xE3: "Measured Cumulative Amount of Electric Energy (Reverse)",
        0xE4: "Historical Data of Measured Cumulative Amount of Electric Energy 1 (Reverse)",
        0xE5: "Day for 1",
        0xE7: "Measured Instantaneous Electric Power",
        0xE8: "Measured Instantaneous Electric Current",
        0xEA: "Cumulative Amount of Electric Energy measured at fixed time (Normal)",
        0xEB: "Cumulative Amount of Electric Energy measured at fixed time (Reverse)",
        0xEC: "Historical Data of Measured Cumulative Amount of Electric Energy 2 (Normal and Reverse)",
        0xED: "Day for 2",
        0xEE: "Historical Data of Measured Cumulative Amount of Electric Energy 3 (Normal and Reverse)",
        0xEF: "Day for 3",
    }
}

def get_epc_name(class_group: int, class_code: int, epc: int) -> str:
    # 1. Try Class Specific
    cls_key = (class_group, class_code)
    if cls_key in CLASS_EPCS:
        if epc in CLASS_EPCS[cls_key]:
            return CLASS_EPCS[cls_key][epc]
            
    # 2. Try Super Class
    if epc in SUPER_CLASS_EPCS:
        return SUPER_CLASS_EPCS[epc]
        
    # 3. Unknown
    return f"Unknown EPC (0x{epc:02X})"

# ECHONET Lite Class Name Mapping
CLASS_NAMES = {
    (0x02, 0x79): "Solar Power Generation",
    (0x02, 0x7D): "Storage Battery", 
    (0x02, 0x88): "Smart Meter",
    (0x0E, 0xF0): "Node Profile"
}

def get_class_name(class_group: int, class_code: int) -> str:
    return CLASS_NAMES.get((class_group, class_code), "Unknown Class")
