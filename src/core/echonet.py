import struct
import logging
from typing import List, Optional, Tuple, Protocol, Dict

# Defines
EHD1 = 0x10
EHD2 = 0x81

# ESV
ESV_SET_I   = 0x60 # SetC but no response required? No, SetI is 60
ESV_SET_C   = 0x61
ESV_GET     = 0x62
ESV_INF_REQ = 0x63
ESV_SET_RES = 0x71
ESV_GET_RES = 0x72
ESV_INF     = 0x73
ESV_SETI_SNA= 0x50
ESV_SETC_SNA= 0x51
ESV_GET_SNA = 0x52

logger = logging.getLogger(__name__)

class EchonetObjectInterface(Protocol):
    def get_property(self, epc: int) -> Optional[bytes]: ...
    def set_property(self, epc: int, data: bytes) -> bool: ...

class EchonetFrame:
    def __init__(self, data: bytes = None):
        self.ehd1 = EHD1
        self.ehd2 = EHD2
        self.tid = 0
        self.seoj = (0x05, 0xFF, 0x01) # Default: Controller
        self.deoj = (0x0E, 0xF0, 0x01) # Default: Node Profile
        self.esv = 0
        self.opc = 0
        self.props: List[Tuple[int, bytes]] = []
        
        if data:
            self.parse(data)
            
    def parse(self, data: bytes):
        if len(data) < 12:
            raise ValueError("Data too short")
        if data[0] != EHD1 or data[1] != EHD2:
            raise ValueError("Invalid EHD")
            
        self.ehd1 = data[0]
        self.ehd2 = data[1]
        self.tid = struct.unpack(">H", data[2:4])[0]
        self.seoj = (data[4], data[5], data[6])
        self.deoj = (data[7], data[8], data[9])
        self.esv = data[10]
        self.opc = data[11]
        
        offset = 12
        for _ in range(self.opc):
            if offset + 2 > len(data): break
            epc = data[offset]
            pdc = data[offset+1]
            offset += 2
            if offset + pdc > len(data): break
            pdt = data[offset : offset+pdc]
            offset += pdc
            self.props.append((epc, pdt))
            
    def to_bytes(self) -> bytes:
        header = struct.pack(">BBHBBB BBB BB", 
            self.ehd1, self.ehd2, self.tid,
            *self.seoj, *self.deoj,
            self.esv, len(self.props)
        )
        body = b""
        for epc, pdt in self.props:
            body += struct.pack("BB", epc, len(pdt)) + pdt
        return header + body

class EchonetController:
    def __init__(self):
        self._objects: Dict[Tuple[int, int, int], EchonetObjectInterface] = {}
        
    def register_instance(self, group: int, code: int, instance: int, handler: EchonetObjectInterface):
        key = (group, code, instance)
        self._objects[key] = handler
        logger.info(f"Registered object: {key}")
        
    def handle_packet(self, data: bytes, source_addr) -> Optional[bytes]:
        try:
            req = EchonetFrame(data)
        except ValueError as e:
            logger.warning(f"Parse error: {e} | Data: {data.hex()}")
            return None
            
        target_key = req.deoj
        
        # 0. Node Profile Handling (Basic Stub)
        if target_key == (0x0E, 0xF0, 0x01):
            # Should handle Node Profile separately or register it as a normal object
            pass
            
        handler = self._objects.get(target_key)
        if not handler:
            logger.debug(f"Unknown target object: {target_key}")
            # Should strictly return SNA (Service Not Available) but ignore for now
            return None
            
        # Process properties
        res_props = []
        is_success = True
        
        for epc, pdt in req.props:
            val = None
            if req.esv == ESV_GET:
                val = handler.get_property(epc)
                if val is not None:
                    res_props.append((epc, val))
                else:
                    # Generic error for Get -> return with count 0 in SNA usually, or 0 length?
                    # ECHONET spec says for Get SNA: copy EPC, PDC=0
                    res_props.append((epc, b"")) # SNA placeholder
                    is_success = False
            elif req.esv in [ESV_SET_I, ESV_SET_C]:
                if handler.set_property(epc, pdt):
                     # For Set response, we usually don't send back data, just EPC and PDC=0
                    res_props.append((epc, b""))
                else:
                    is_success = False
            
        # Determine Response ESV
        res_esv = 0
        if req.esv == ESV_GET:
            res_esv = ESV_GET_RES if is_success else ESV_GET_SNA
        elif req.esv == ESV_SET_C:
            res_esv = ESV_SET_RES if is_success else ESV_SETC_SNA
        elif req.esv == ESV_SET_I:
            # SET_I usually doesn't require response unless error? 
            # Actually SetI (60) often expects no response, but SetC (61) does.
            # If implementation requires reliable, use SetC.
            # If we succeed SetI, we return nothing usually?
            # ECHONET spec: ESV 0x60 -> 0x7E (SetGet_Res) is not for this.
            # Actually SetI is "Set Request (no response required)". 
            # But we might send response if it fails (SNA)?
            # Keep it simple: if SetI and success -> None.
            return None 

        if not res_esv:
            return None

        # Build Response
        res = EchonetFrame()
        res.tid = req.tid
        res.seoj = req.deoj # Swap Source/Dest
        res.deoj = req.seoj
        res.esv = res_esv
        res.props = res_props
        
        return res.to_bytes()

# Global ECHONET Controller
echonet_ctrl = EchonetController()
