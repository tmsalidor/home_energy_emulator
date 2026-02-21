import asyncio
import logging
import socket
import struct
from src.config.settings import settings
from src.core.echonet import wifi_echonet_ctrl, wisun_echonet_ctrl
from src.core.adapters import SolarAdapter, BatteryAdapter, NodeProfileAdapter, SmartMeterAdapter, ElectricWaterHeaterAdapter
from src.core.wisun import wisun_manager
from src.core.engine import engine

logger = logging.getLogger("uvicorn")

class EchonetProtocol(asyncio.DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport
        logger.info(f"ECHONET Lite UDP Server (Wi-Fi) listening on port {settings.communication.echonet_port}")

    def datagram_received(self, data, addr):
        # Dispatch to Wi-Fi controller
        # Note: addr is (ip, port)
        res = wifi_echonet_ctrl.handle_packet(data, addr)
        if res:
            self.transport.sendto(res, addr)

async def start_echonet_service():
    # --- 1. Wi-Fi Controller Setup (Solar + Battery) ---
    # --- 1. Wi-Fi Controller Setup (Solar + Battery) ---
    # Node Profile for Wi-Fi: Solar(0279) and Battery(027D)
    
    wifi_instances = []
    
    # Always check settings for enabled devices
    enabled_devs = settings.echonet.wifi_devices
    
    if 'solar' in enabled_devs:
        wifi_instances.append((0x02, 0x79, 0x01))
        
    if 'battery' in enabled_devs:
        wifi_instances.append((0x02, 0x7D, 0x01))

    if 'water_heater' in enabled_devs:
        wifi_instances.append((0x02, 0x6B, 0x01))
        
    wifi_echonet_ctrl.register_instance(0x0E, 0xF0, 0x01, NodeProfileAdapter(wifi_instances))
    
    if 'solar' in enabled_devs:
        wifi_echonet_ctrl.register_instance(0x02, 0x79, 0x01, SolarAdapter(engine.solar))
        
    if 'battery' in enabled_devs:
        wifi_echonet_ctrl.register_instance(0x02, 0x7D, 0x01, BatteryAdapter(engine.battery))

    if 'water_heater' in enabled_devs:
        wifi_echonet_ctrl.register_instance(0x02, 0x6B, 0x01, ElectricWaterHeaterAdapter(engine.water_heater))
    
    # --- 2. Wi-SUN Controller Setup (Smart Meter) ---
    # Node Profile for Wi-SUN: Smart Meter(0288)
    wisun_instances = [(0x02, 0x88, 0x01)]
    wisun_echonet_ctrl.register_instance(0x0E, 0xF0, 0x01, NodeProfileAdapter(wisun_instances))
    
    # Smart Meter: Class Group 0x02, Class Code 0x88, Instance 0x01
    wisun_echonet_ctrl.register_instance(0x02, 0x88, 0x01, SmartMeterAdapter(engine.smart_meter))

    
    # --- 3. Start UDP Server (Wi-Fi) with Multicast Support ---
    try:
        loop = asyncio.get_running_loop()
        
        # Create Socket manually for Multicast
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Bind to all interfaces
        sock.bind(('0.0.0.0', settings.communication.echonet_port))
        
        # Join Multicast Group 224.0.23.0
        mreq = struct.pack("4sl", socket.inet_aton("224.0.23.0"), socket.INADDR_ANY)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        
        # Set Multicast TTL
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
        
        await loop.create_datagram_endpoint(
            lambda: EchonetProtocol(),
            sock=sock
        )
        logger.info("ECHONET Lite UDP Server started with Multicast (224.0.23.0) support.")

        # --- 3.5 Send Instance List Notification (INF) ---
        # Announce presence to the network via Multicast
        try:
            # 1. Get Instance List (D5) from Node Profile
            # Node Profile instance tuple: (0x0E, 0xF0, 0x01)
            node_profile = wifi_echonet_ctrl._objects.get((0x0E, 0xF0, 0x01))
            if node_profile:
                d5_value = node_profile.get_property(0xD5) # Instance List Notification
                if d5_value:
                    # 2. Build ECHONET Lite Frame (Format 1)
                    # EHD(2) + TID(2) + SEOJ(3) + DEOJ(3) + ESV(1) + OPC(1) + EPC(1) + PDC(1) + EDT(N)
                    tid = b'\x00\x00' # Transaction ID
                    seoj = b'\x0E\xF0\x01' # Source: Node Profile
                    deoj = b'\x0E\xF0\x01' # Dest: Node Profile (Broadcast to all nodes)
                    esv = b'\x73' # INF (Property Value Notification)
                    opc = b'\x01'
                    epc = b'\xD5'
                    pdc = bytes([len(d5_value)])
                    edt = d5_value
                    
                    frame = b'\x10\x81' + tid + seoj + deoj + esv + opc + epc + pdc + edt
                    
                    # 3. Send to Multicast
                    sock.sendto(frame, ('224.0.23.0', 3610))
                    logger.info("Sent Initial Instance List Notification (INF) to 224.0.23.0:3610")
        except Exception as e:
            logger.error(f"Failed to send initial announcement: {e}")
            
    except Exception as e:
        logger.error(f"Failed to start UDP server: {e}")

    # 4. Start Wi-SUN Manager (B-Route)
    asyncio.create_task(wisun_manager.start())
