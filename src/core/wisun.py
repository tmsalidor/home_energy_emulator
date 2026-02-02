import asyncio
import logging
from typing import Optional, Callable
import serial_asyncio
from src.config.settings import settings
from src.core.echonet import wisun_echonet_ctrl

logger = logging.getLogger("uvicorn")

class SerialInterface:
    def __init__(self, device_path: str, baudrate: int = 115200):
        self.device_path = device_path
        self.baudrate = baudrate
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None

    async def connect(self):
        logger.info(f"Attempting to connect to serial port: {self.device_path} Baud:{self.baudrate}")
        try:
            self.reader, self.writer = await serial_asyncio.open_serial_connection(
                url=self.device_path, baudrate=self.baudrate
            )
            logger.info(f"Connected to Wi-SUN dongle at {self.device_path}")
        except Exception as e:
            logger.debug(f"Failed to connect to Wi-SUN dongle: {e}")
            raise

    async def write_line(self, line: str):
        if not self.writer: return
        data = (line + "\r\n").encode('utf-8')
        self.writer.write(data)
        await self.writer.drain()
        logger.info(f"TX: {line}")

    async def read_line_forever(self, callback: Callable[[str], None]):
        if not self.reader:
             logger.error("Reader is None in read_line_forever")
             return
        logger.info("Starting serial read loop")
        while True:
            try:
                line_bytes = await self.reader.readline()
                if not line_bytes:
                    break
                line = line_bytes.decode('utf-8').strip()
                if line:
                    logger.info(f"RX: {line}")
                    callback(line)
            except Exception as e:
                logger.error(f"Serial read error: {e}")
                await asyncio.sleep(1)

class WiSunManager:
    def __init__(self):
        self.serial = SerialInterface(settings.communication.wi_sun_device)
        self.is_running = False
        self.scan_active = False
        self._response_future: Optional[asyncio.Future] = None
        
    async def start(self):
        logger.info("WiSunManager.start() called")
        try:
            await self.serial.connect()
            self.is_running = True
            
            # Start reader task
            asyncio.create_task(self.serial.read_line_forever(self._handle_serial_line))
            
            # Initialize SK Stack
            await self._initialize_stack()
            
        except Exception as e:
            logger.warning(f"Wi-SUN Dongle not found or failed to connect. Wi-SUN features will be disabled. Error: {e}")

    async def _send_command_wait_ok(self, cmd: str, timeout: float = 2.0) -> bool:
        self._response_future = asyncio.Future()
        await self.serial.write_line(cmd)
        try:
            res = await asyncio.wait_for(self._response_future, timeout)
            return res == "OK"
        except asyncio.TimeoutError:
            logger.warning(f"Command timeout: {cmd}")
            return False
        finally:
            self._response_future = None

    async def _initialize_stack(self):
        logger.info("Initializing Wi-SUN Stack...")
        
        # 1. Reset
        await self.serial.write_line("SKRESET")
        await asyncio.sleep(2.0) # Wait for reboot
        
        # 2. Set Password
        pwd = settings.communication.b_route_password
        if not await self._send_command_wait_ok(f"SKSETPWD C {pwd}"):
            logger.error("Failed to set password")
            return
            
        # 3. Set RBID
        rbid = settings.communication.b_route_id
        if not await self._send_command_wait_ok(f"SKSETRBID {rbid}"):
            logger.error("Failed to set RBID")
            return
            
        # 4. Initialize Register (Specifically Channel if needed, simple SKSREG S2 30 for now?)
        # For Coordinator, might scan or set specific channel.
        # Let's assume default or specific setup.
        # Check channel from settings
        # ch = settings.communication.wi_sun_channel
        # if ch:
        #    await self._send_command_wait_ok(f"SKSREG S2 {ch}")
        
        # 5. Start PANA (Coordinator Mode)
        # SKSTART: Start HAN functionality
        if await self._send_command_wait_ok("SKSTART"):
             logger.info("Wi-SUN Stack Started (Coordinator Mode)")
        else:
             logger.error("Failed to start Wi-SUN Stack")

    def _handle_serial_line(self, line: str):
        # 1. Command Response Handling
        if self._response_future and not self._response_future.done():
            if line == "OK":
                self._response_future.set_result("OK")
            elif line.startswith("FAIL"):
                self._response_future.set_result("FAIL")

        # 2. Event Handling
        if line.startswith("EVENT"):
            self._handle_event(line)
            
        # 3. Data Reception (ERXUDP)
        if line.startswith("ERXUDP"):
            self._handle_erxudp(line)

    def _handle_event(self, line: str):
        parts = line.split()
        if len(parts) < 3: return
        num = parts[1]
        
        if num == "21": # UDP Send Completed
            pass
        elif num == "25": # PANA Connection Success
            logger.info(f"PANA Connection Established with {parts[2]}")
        elif num == "02": # Neighbor Advertisement Received
            pass

    def _handle_erxudp(self, line: str):
        # ERXUDP <SENDER> <DEST> <RPORT> <LPORT> <SENDERLLA> <SECURED> <DATALEN> <DATA>
        try:
            parts = line.split()
            if len(parts) < 9: return
            
            sender_ip = parts[1]
            lport_hex = parts[4]
            # sender_lla = parts[5]
            # secured = parts[6]
            # datalen = int(parts[7], 16)
            data_hex = parts[8]

            # Log all received UDP packets for debugging/verification
            logger.info(f"RX UDP | Sender:{sender_ip} Port:{lport_hex} Data:{data_hex}")

            # Filter Port: ECHONET Lite uses 3610 (0x0E1A)
            # Some devices might trigger ERXUDP for PANA (0x02D3/723 or others)
            if lport_hex.upper() != "0E1A":
                logger.debug(f"Skipping non-ECHONET Lite packet (Port {lport_hex})")
                return
            
            data_bytes = bytes.fromhex(data_hex)
            
            # Dispatch to ECHONET Lite Controller
            # We need to map Wi-SUN sender to an abstract address if needed, or just pass context
            # For now, treat sender_ip as identifier
            
            logger.info(f"Received ECHONET packet from {sender_ip}")
            
            # Use Echonet Controller to process
            response_bytes = wisun_echonet_ctrl.handle_packet(data_bytes, (sender_ip, 3610))
            
            if response_bytes:
                # Send response back via SKSENDTO
                # SKSENDTO <HANDLE> <IPADDR> <PORT> <SECURE> <DATALEN> <DATA>
                asyncio.create_task(self._send_udp(sender_ip, 3610, response_bytes))
                
        except Exception as e:
            logger.error(f"Failed to handle ERXUDP: {e}")
            
    async def _send_udp(self, ip: str, port: int, data: bytes):
        handle = "1"
        secured = "1" # Always encrypted for B-route
        datalen = f"{len(data):04X}"
        data_str = data.hex() # data must be hex string if binary? No, SKSENDTO expects data.
        # Usually SKSENDTO takes raw data, but pyserial write utf-8.
        # Actually SKSENDTO format depends on mode. Usually binary data follows.
        # But here we writing to text mode serial. 
        # Typically SKSTACK accepts binary data, but here we construct command string.
        # Wait, SKSENDTO expects data to be written?
        # Specification: SKSENDTO <Handle> <IPaddr> <Port> <Sec> <DataLen> <Data>
        # If we use pyserial, we should be careful about binary data in string.
        # It's safer to send data as is? No, SKSENDTO command line includes data?
        # Actually, standard SKSTACK might vary.
        # Some emulators expect hex string, some expect binary. 
        # ROHM spec: Data is raw binary.
        # We need to write line up to DataLen, then write raw bytes.
        
        header = f"SKSENDTO {handle} {ip} {port:04X} {secured} {datalen:.4} " # Space at end?
        # SKSENDTO handle ip port sec datalen data
        # Let's write header then data
        # datalen is hex length of data bytes
        
        # NOTE: This implementation assumes we can write bytes to the serial writer
        if not self.serial.writer: return
        
        cmd = f"SKSENDTO {handle} {ip} {port:04X} {secured} {len(data):04X} "
        self.serial.writer.write(cmd.encode('utf-8'))
        self.serial.writer.write(data)
        # self.serial.writer.write(b'\r\n') # Normally no CRLF after data? Check spec. 
        # Usually no CRLF after data block for binary mode send? 
        # Or SKSTACK consumes exactly datalen bytes.
        
        await self.serial.writer.drain()
        logger.debug(f"UDP Sent to {ip}: {len(data)} bytes")

# Global Instance
wisun_manager = WiSunManager()
