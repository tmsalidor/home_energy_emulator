# ECHONET Lite Property Name Mapping

EPC_NAMES = {
    # Super Class / Common
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
    0x9D: "Status Change Announcement Property Map",
    0x9E: "Set Property Map",
    0x9F: "Get Property Map",
    
    # Node Profile (0x0EF0)
    0xD3: "Self-node Instances Total Number",
    0xD4: "Self-node Instances List",
    0xD5: "Instance List Notification",
    0xD6: "Self-node Instance List S",
    0xD7: "Self-node Class List S",

    # Solar Power (0x0279)
    0xE0: "Instantaneous Amount of Electricity Generated",
    0xE1: "Cumulative Amount of Electricity Generated",
    0xE2: "Reset Cumulative Amount of Electricity Generated",
    0xE3: "Cumulative Amount of Electricity Generated (Reverse)",
    0xE4: "Instantaneous Amount of Electricity Generated (Reverse)",
    
    # Storage Battery (0x027D)
    # 0xD3 is Working Operation Status shared? or specific?
    # Actually 0xD3 in Super Class is something else, but in Battery it is Working Operation Status (collision in definition depending on context? No, Super Class 0x80-0x9F. Device specific starts from 0x?? usually A0 or so but specific classes reuse others)
    # Let's populate specific ones.
    # Battery
    # 0xD3: Working Operation Status (Battery specific) - Overrides generic?
    # Wait, 0x80-0x9F are common. Others are class specific.
    0xA0: "AC Effective Capacity (Charge)",
    0xA1: "AC Effective Capacity (Discharge)",
    0xA2: "AC Chargeable Capacity",
    0xA3: "AC Dischargeable Capacity",
    0xA4: "AC Chargeable Amount",
    0xA5: "AC Dischargeable Amount",
    0xA6: "Charge Upper Limit Setting",
    0xA7: "Discharge Lower Limit Setting",
    0xA8: "Remaining Capacity 1",
    0xA9: "Remaining Capacity 3",
    0xAA: "Battery State of Health",
    0xAB: "Charging Efficiency",
    0xAC: "Discharging Efficiency",
    0xD0: "Rated Electric Energy Capacity (Factory)",
    0xD2: "Rated Capacity",
    # 0xD3 is duplicate key if we put in single dict. We might need logic.
    # For now, put common name or specialized name.
    # 0xE2: Rated Electric Energy Capacity
    # 0xE3: Remaining Capacity 2 (SOC)
    # 0xE4: Status 2
    
    # Smart Meter (0x0288)
    0xE7: "Instantaneous Electric Power",
    
    # Handing duplicates/context:
    # We will use this map as fallback or generic lookup.
}

def get_epc_name(class_group: int, class_code: int, epc: int) -> str:
    # Specific Overrides
    if class_group == 0x02 and class_code == 0x7D: # Battery
        if epc == 0xD3: return "Working Operation Status"
        if epc == 0xE2: return "Rated Electric Energy Capacity"
        if epc == 0xE3: return "Remaining Capacity (SOC)"
        
    if class_group == 0x02 and class_code == 0x88: # Smart Meter
        if epc == 0xE0: return "Cumulative Amount of Electric Energy (Normal)"
        if epc == 0xE1: return "Unit for Cumulative Amounts"
        if epc == 0xE3: return "Cumulative Amount of Electric Energy (Reverse)"
    
    # Default Lookup
    return EPC_NAMES.get(epc, f"Unknown EPC (0x{epc:02X})")
