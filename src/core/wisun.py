import asyncio
import logging
import re
from typing import Optional, Callable
import serial_asyncio
from src.config.settings import settings
from src.core.echonet import wisun_echonet_ctrl
from src.core.wisun_dongle import (
    DongleProfile, SKSTACK_A1, BP35C0, profile_by_name, guess_profile,
    parse_erxudp, parse_event, build_sendto_header, resolve_device_path,
)

logger = logging.getLogger("uvicorn")

# ROPT の返答は CR だけで終わるので、CR / LF のどちらでも行を区切る
_LINE_SPLIT = re.compile(rb"\r\n|\r|\n")


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
        self.writer.write((line + "\r\n").encode('utf-8'))
        await self.writer.drain()
        logger.info(f"TX: {line}")

    async def write_bytes(self, data: bytes):
        if not self.writer: return
        self.writer.write(data)
        await self.writer.drain()

    async def read_line_forever(self, callback: Callable[[str], None]):
        if not self.reader:
            logger.error("Reader is None in read_line_forever")
            return
        logger.info("Starting serial read loop")
        buf = b""
        while True:
            try:
                chunk = await self.reader.read(1024)
                if not chunk:
                    break
                buf += chunk
                pieces = _LINE_SPLIT.split(buf)
                buf = pieces.pop()  # 最後は区切りがまだ来ていない途中の行
                for raw in pieces:
                    line = raw.decode('utf-8', errors='replace').strip()
                    if line:
                        logger.info(f"RX: {line}")
                        callback(line)
            except Exception as e:
                logger.error(f"Serial read error: {e}")
                await asyncio.sleep(1)


class _PendingCommand:
    def __init__(self, collect_prefix: Optional[str]):
        self.collect_prefix = collect_prefix
        self.lines: list[str] = []
        self.future: asyncio.Future = asyncio.get_running_loop().create_future()


class WiSunManager:
    def __init__(self):
        self.serial: Optional[SerialInterface] = None
        self.is_running = False
        self.scan_active = False
        self._pending: Optional[_PendingCommand] = None

        # ドングルの種類 (起動時に当たりを付け、最初の ERXUDP で確定する)
        self.profile: DongleProfile = SKSTACK_A1
        self.profile_reason: str = "未検出"
        self.profile_confirmed: bool = False
        self.profile_forced: bool = False
        self.device_info: dict[str, str] = {}

    @property
    def status_text(self) -> str:
        if not self.is_running:
            return "未接続"
        state = "固定" if self.profile_forced else ("確定" if self.profile_confirmed else "推定")
        return f"{self.profile.label} [{state}] ({self.profile_reason})"

    async def start(self):
        logger.info("WiSunManager.start() called")
        try:
            path, note = resolve_device_path(settings.communication.wi_sun_device)
            if note:
                logger.info(note)
            self.serial = SerialInterface(path)
            await self.serial.connect()
            self.is_running = True

            asyncio.create_task(self.serial.read_line_forever(self._handle_serial_line))

            await self._initialize_stack()

        except Exception as e:
            logger.warning(f"Wi-SUN Dongle not found or failed to connect. Wi-SUN features will be disabled. Error: {e}")

    async def _send_command(self, cmd: str, timeout: float = 2.0,
                            collect_prefix: Optional[str] = None) -> tuple[Optional[str], list[str]]:
        """コマンドを送って OK / FAIL を待つ。

        戻り値は (結果, collect_prefix で始まる返答行)。
        結果は "OK" / "OK <値>" / "FAIL ..." / None (時間切れ)。
        """
        pending = _PendingCommand(collect_prefix)
        self._pending = pending
        await self.serial.write_line(cmd)
        try:
            res = await asyncio.wait_for(pending.future, timeout)
            return res, pending.lines
        except asyncio.TimeoutError:
            logger.warning(f"Command timeout: {cmd}")
            return None, pending.lines
        finally:
            self._pending = None

    async def _send_command_wait_ok(self, cmd: str, timeout: float = 2.0) -> bool:
        res, _ = await self._send_command(cmd, timeout)
        return res is not None and res.startswith("OK")

    async def _query(self, cmd: str, prefix: str) -> Optional[str]:
        _, lines = await self._send_command(cmd, collect_prefix=prefix)
        return lines[0] if lines else None

    async def _detect_dongle(self):
        for cmd, prefix in (("SKVER", "EVER"), ("SKAPPVER", "EAPPVER"), ("SKINFO", "EINFO")):
            value = await self._query(cmd, prefix)
            if value:
                self.device_info[prefix] = value
        logger.info(f"Wi-SUN dongle info: {self.device_info or '(返答なし)'}")

        forced = profile_by_name(settings.communication.wi_sun_dongle)
        if forced:
            self.profile = forced
            self.profile_reason = f"設定 wi_sun_dongle={forced.name}"
            self.profile_forced = True
        else:
            self.profile, self.profile_reason = guess_profile(
                self.device_info.get("EVER"), self.device_info.get("EAPPVER"), self.device_info.get("EINFO"))
        logger.info(f"Wi-SUN dongle type: {self.profile.name} ({self.profile_reason})")

    async def _ensure_hex_payload(self):
        """受信データ (ERXUDP) を 16 進文字で出す設定にする。

        ROPT の返答 "OK 00" は生バイト、"OK 01" は 16 進文字。
        WOPT はフラッシュに書くので、必要なときだけ送る。
        """
        res, _ = await self._send_command("ROPT")
        if res is None or not res.startswith("OK"):
            logger.warning(f"ROPT に応答がありません ({res})。受信データの形式は変更しません")
            return
        mode = res[2:].strip()
        if mode == "01":
            logger.info("ERXUDP payload mode: hex ASCII (ROPT=01)")
            return
        logger.info(f"ERXUDP payload mode is {mode or '?'}; switching to hex ASCII with WOPT 01")
        if not await self._send_command_wait_ok("WOPT 01"):
            logger.error("WOPT 01 に失敗しました。ERXUDP を読めない可能性があります")

    async def _initialize_stack(self):
        logger.info("Initializing Wi-SUN Stack...")

        # 1. Reset
        await self.serial.write_line("SKRESET")
        # リセット後は 3 秒以上待ってからアクセスする (ROHM BP35C0 サンプルスクリプト説明書 5.5)
        await asyncio.sleep(3.0)

        # ドングルの種類を確かめる (SKVER / SKAPPVER / SKINFO)
        await self._detect_dongle()

        if self.profile.check_payload_mode:
            await self._ensure_hex_payload()

        if not await self._send_command_wait_ok("SKSREG S2 29"):
            logger.error("Failed to set SKSREG S2 29")
            return

        if not await self._send_command_wait_ok("SKSREG S3 CAFE"):
            logger.error("Failed to set SKSREG S3 CAFE")
            return

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

        # 4. Start PANA (PAA / Coordinator Mode)
        if await self._send_command_wait_ok("SKSTART"):
            logger.info(f"Wi-SUN Stack Started (Coordinator Mode, dongle={self.profile.name})")
        else:
            logger.error(f"Failed to start Wi-SUN Stack (dongle={self.profile.name})")

    def _handle_serial_line(self, line: str):
        # 1. Command Response Handling
        pending = self._pending
        if pending and not pending.future.done():
            if pending.collect_prefix and line.startswith(pending.collect_prefix + " "):
                pending.lines.append(line)
            elif line == "OK" or line.startswith("OK "):
                pending.future.set_result(line)
            elif line.startswith("FAIL"):
                pending.future.set_result(line)

        # 2. Event Handling
        if line.startswith("EVENT"):
            self._handle_event(line)

        # 3. Data Reception (ERXUDP)
        if line.startswith("ERXUDP"):
            self._handle_erxudp(line)

    def _handle_event(self, line: str):
        ev = parse_event(line, self.profile)
        if not ev:
            return
        if ev.num == "25": # PANA Connection Success
            logger.info(f"PANA Connection Established with {ev.sender}")
        elif ev.num == "21" and ev.param not in (None, "00"): # UDP Send Completed
            logger.info(f"UDP send to {ev.sender} completed with PARAM={ev.param}")

    def _confirm_profile_from_erxudp(self, has_side: bool):
        """最初の ERXUDP の項目数で SIDE の有無を確定する。"""
        if self.profile_confirmed:
            return
        self.profile_confirmed = True
        if has_side == self.profile.has_side:
            logger.info(f"Wi-SUN dongle type confirmed by ERXUDP: {self.profile.name}")
            return
        observed = "SIDE あり" if has_side else "SIDE なし"
        if self.profile_forced:
            logger.warning(f"ERXUDP は {observed} の形式ですが、設定で {self.profile.name} に固定されています")
            return
        new = BP35C0 if has_side else SKSTACK_A1
        logger.warning(f"ERXUDP が {observed} の形式のため、ドングルの種類を {self.profile.name} → {new.name} に切り替えます")
        self.profile = new
        self.profile_reason = f"ERXUDP の形式 ({observed})"

    def _handle_erxudp(self, line: str):
        try:
            pkt = parse_erxudp(line)
            if not pkt:
                logger.warning(f"Unrecognized ERXUDP line: {line}")
                return

            self._confirm_profile_from_erxudp(pkt.has_side)

            logger.info(f"RX UDP | Sender:{pkt.sender} Port:{pkt.lport} Data:{pkt.data_hex}")

            # ECHONET Lite (3610 = 0x0E1A) 以外 (PANA 0x02CC など) は無視する
            if pkt.lport.upper() != "0E1A":
                logger.debug(f"Skipping non-ECHONET Lite packet (Port {pkt.lport})")
                return

            if not pkt.is_hex_payload:
                logger.warning("ERXUDP のデータが 16 進文字ではありません (生バイトの設定の可能性)。パケットを捨てます")
                return

            data_bytes = bytes.fromhex(pkt.data_hex)
            logger.info(f"Received ECHONET packet from {pkt.sender}")

            response_bytes = wisun_echonet_ctrl.handle_packet(data_bytes, (pkt.sender, 3610))
            if response_bytes:
                asyncio.create_task(self._send_udp(pkt.sender, 3610, response_bytes))

        except Exception as e:
            logger.error(f"Failed to handle ERXUDP: {e}")

    async def _send_udp(self, ip: str, port: int, data: bytes):
        # SKSENDTO はヘッダの後にデータを生バイトで続ける (末尾の CRLF は不要)
        if not self.serial or not self.serial.writer: return
        header = build_sendto_header(self.profile, ip, port, len(data), secured="1")
        await self.serial.write_bytes(header + data)
        logger.info(f"TX UDP | {header.decode('ascii').strip()} Data:{data.hex().upper()}")

# Global Instance
wisun_manager = WiSunManager()
