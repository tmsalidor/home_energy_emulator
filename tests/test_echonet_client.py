import socket
import struct
import time

# Constants
EHD1 = 0x10
EHD2 = 0x81
TID = 0x0001
SEJ = (0x05, 0xFF, 0x01) # Controller
DEJ = (0x02, 0x79, 0x01) # Solar
ESV_GET = 0x62
EPC_INSTANT_POWER = 0xE0

def build_frame():
    # Header: EHD1, EHD2, TID (2), SEOJ (3), DEOJ (3), ESV (1), OPC (1)
    # Payload: EPC (1), PDC (1)
    header = struct.pack(">BBHBBB BBB BB", 
        EHD1, EHD2, TID,
        *SEJ, *DEJ,
        ESV_GET, 1 # OPC=1
    )
    # EPC=0xE0, PDC=0
    prop = struct.pack("BB", EPC_INSTANT_POWER, 0)
    return header + prop

def parse_response(data):
    if len(data) < 12: return "Too short"
    esv = data[10]
    if esv == 0x72: # Get_Res
        # Parse property
        # Offset 12
        epc = data[12]
        pdc = data[13]
        if epc == EPC_INSTANT_POWER:
            val = struct.unpack(">H", data[14:14+pdc])[0]
            return f"Success! Solar Output: {val} W"
    return f"Unknown response ESV: {hex(esv)}"

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    server_address = ('127.0.0.1', 3610)
    msg = build_frame()
    
    print(f"Sending ECHONET GET to {server_address}...")
    try:
        sock.sendto(msg, server_address)
        
        data, server = sock.recvfrom(1024)
        print(f"Received {len(data)} bytes from {server}")
        print(parse_response(data))
        
    except socket.timeout:
        print("Timeout: No response from emulator.")
    finally:
        sock.close()

if __name__ == "__main__":
    main()
