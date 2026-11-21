"""Wi-SUN ドングルの自動判別と行の読み書きのテスト (実機なし)

実行: PYTHONPATH=. python -m unittest tests/test_wisun_dongle.py -v
"""
import asyncio
import unittest
from unittest import mock

from src.core.wisun_dongle import (
    SKSTACK_A1, BP35C0, guess_profile, parse_erxudp, parse_event,
    build_sendto_header, profile_by_name, resolve_device_path,
)

# 実機 (TESSERA) で受けていた形式の例 (SIDE なし・9 項目)
ERXUDP_A1 = ("ERXUDP FE80:0000:0000:0000:021D:1290:1234:5678 FE80:0000:0000:0000:021D:1290:0003:C890 "
             "0E1A 0E1A 001D129012345678 1 000E 1081000105FF010288016201E700")
# BP35C0 の形式の例 (SIDE あり・10 項目)
ERXUDP_C0 = ("ERXUDP FE80:0000:0000:0000:021D:1290:1234:5678 FE80:0000:0000:0000:021D:1290:0003:C890 "
             "0E1A 0E1A 001D129012345678 1 0 000E 1081000105FF010288016201E700")


# ROHM サンプルスクリプト説明書 図10 の BP35C0 の実際の行 (PANA, 受信データは初期設定の生バイト)
ERXUDP_C0_ROHM_PANA = ("ERXUDP FE80:0000:0000:0000:021D:1291:0000:05B9 FE80:0000:0000:0000:021D:1291:0000:00D5 "
                       "02CC 02CC 001D1291000005B9 0 0 0044 D\"'")


class TestRohmDoc(unittest.TestCase):
    """ROHM の資料に載っている BP35C0 の実際の返答で確かめる"""

    def test_skver_skappver(self):
        self.assertIs(guess_profile("EVER 1.5.2", "EAPPVER rev15")[0], BP35C0)

    def test_erxudp_pana_binary(self):
        p = parse_erxudp(ERXUDP_C0_ROHM_PANA)
        self.assertTrue(p.has_side)
        self.assertEqual((p.secured, p.side, p.datalen, p.lport), ("0", "0", 0x44, "02CC"))
        self.assertFalse(p.is_hex_payload)

    def test_events(self):
        e = parse_event("EVENT 21 FE80:0000:0000:0000:021D:1291:0000:05B9 0 00", BP35C0)
        self.assertEqual((e.num, e.side, e.param), ("21", "0", "00"))
        e = parse_event("EVENT 25 FE80:0000:0000:0000:021D:1291:0000:05B9 0", BP35C0)
        self.assertEqual((e.num, e.side, e.param), ("25", "0", None))


class TestParse(unittest.TestCase):
    def test_erxudp_without_side(self):
        p = parse_erxudp(ERXUDP_A1)
        self.assertIsNotNone(p)
        self.assertFalse(p.has_side)
        self.assertEqual(p.lport, "0E1A")
        self.assertEqual(p.datalen, 14)
        self.assertTrue(p.is_hex_payload)

    def test_erxudp_with_side(self):
        p = parse_erxudp(ERXUDP_C0)
        self.assertTrue(p.has_side)
        self.assertEqual(p.side, "0")
        self.assertEqual(p.data_hex, "1081000105FF010288016201E700")
        self.assertTrue(p.is_hex_payload)

    def test_erxudp_bad(self):
        self.assertIsNone(parse_erxudp("ERXUDP a b c"))
        self.assertIsNone(parse_erxudp("EVENT 25 FE80::1"))

    def test_binary_payload_detected(self):
        p = parse_erxudp(ERXUDP_A1.replace("1081000105FF010288016201E700", "\x10\x81"))
        self.assertFalse(p.is_hex_payload)

    def test_event(self):
        e = parse_event("EVENT 21 FE80::1 02", SKSTACK_A1)
        self.assertEqual((e.num, e.sender, e.side, e.param), ("21", "FE80::1", None, "02"))
        e = parse_event("EVENT 21 FE80::1 0 01", BP35C0)
        self.assertEqual((e.num, e.sender, e.side, e.param), ("21", "FE80::1", "0", "01"))
        e = parse_event("EVENT 25 FE80::1", SKSTACK_A1)
        self.assertEqual((e.num, e.param), ("25", None))


class TestBuild(unittest.TestCase):
    def test_sendto_a1(self):
        self.assertEqual(build_sendto_header(SKSTACK_A1, "FE80::1", 3610, 0x1E),
                         b"SKSENDTO 1 FE80::1 0E1A 1 001E ")

    def test_sendto_c0(self):
        self.assertEqual(build_sendto_header(BP35C0, "FE80::1", 3610, 0x1E),
                         b"SKSENDTO 1 FE80::1 0E1A 1 0 001E ")


class TestGuess(unittest.TestCase):
    def test_guess(self):
        self.assertIs(guess_profile("EVER 1.5.2")[0], BP35C0)
        self.assertIs(guess_profile("EVER 1.2.10")[0], SKSTACK_A1)
        self.assertIs(guess_profile(None)[0], SKSTACK_A1)

    def test_profile_by_name(self):
        self.assertIs(profile_by_name("bp35c0"), BP35C0)
        self.assertIs(profile_by_name("BP35C0 "), BP35C0)
        self.assertIsNone(profile_by_name("auto"))

    def test_resolve_device_path(self):
        with mock.patch("os.path.exists", return_value=False), \
             mock.patch("src.core.wisun_dongle.find_serial_candidates", return_value=["/dev/ttyACM0"]):
            path, note = resolve_device_path("/dev/ttyUSB0")
        self.assertEqual(path, "/dev/ttyACM0")
        self.assertIn("ttyACM0", note)
        self.assertEqual(resolve_device_path("COM3"), ("COM3", None))


class TestReadLoop(unittest.TestCase):
    def test_cr_only_and_split_chunks(self):
        """ROPT の返答のように CR だけで終わる行や、途中で分かれて届く行も 1 行ずつ渡す"""
        from src.core.wisun import SerialInterface

        async def main():
            s = SerialInterface("dummy")
            s.reader = asyncio.StreamReader()
            got = []
            s.reader.feed_data(b"ROPT\r\nOK 00\rEVER 1.")
            s.reader.feed_data(b"5.2\r\nOK\r\n")
            s.reader.feed_eof()
            await s.read_line_forever(got.append)
            return got

        self.assertEqual(asyncio.run(main()), ["ROPT", "OK 00", "EVER 1.5.2", "OK"])


class FakeSerial:
    """書かれたコマンドに決まった返答を返す偽のシリアル"""

    def __init__(self, manager, replies):
        self.manager = manager
        self.replies = replies
        self.written = []
        self.writer = True

    async def write_line(self, line):
        self.written.append(line)
        for reply in self.replies.get(line.split()[0], ["OK"]):
            asyncio.get_running_loop().call_soon(self.manager._handle_serial_line, reply)

    async def write_bytes(self, data):
        self.written.append(data)


def run_init(replies, dongle_setting="auto"):
    from src.core.wisun import WiSunManager
    from src.config.settings import settings

    async def main():
        m = WiSunManager()
        m.serial = FakeSerial(m, replies)
        m.is_running = True
        with mock.patch.object(settings.communication, "wi_sun_dongle", dongle_setting), \
             mock.patch("asyncio.sleep", new=mock.AsyncMock()):
            await m._initialize_stack()
        return m

    return asyncio.run(main())


class TestManager(unittest.TestCase):
    def test_init_tessera(self):
        m = run_init({"SKRESET": [], "SKVER": ["EVER 1.2.10", "OK"]})
        self.assertIs(m.profile, SKSTACK_A1)
        cmds = [c for c in m.serial.written if isinstance(c, str)]
        self.assertNotIn("ROPT", cmds)
        self.assertEqual(cmds[-1], "SKSTART")

    def test_init_bp35c0_switches_to_hex(self):
        m = run_init({"SKRESET": [], "SKVER": ["EVER 1.5.2", "OK"], "SKAPPVER": ["EAPPVER rev15", "OK"], "ROPT": ["OK 00"]})
        self.assertIs(m.profile, BP35C0)
        cmds = [c for c in m.serial.written if isinstance(c, str)]
        self.assertIn("WOPT 01", cmds)
        self.assertEqual(cmds[-1], "SKSTART")

    def test_init_bp35c0_already_hex(self):
        m = run_init({"SKRESET": [], "SKVER": ["EVER 1.5.2", "OK"], "ROPT": ["OK 01"]})
        self.assertNotIn("WOPT 01", m.serial.written)

    def test_forced_setting(self):
        m = run_init({"SKRESET": [], "SKVER": ["EVER 1.2.10", "OK"], "ROPT": ["OK 01"]}, "bp35c0")
        self.assertIs(m.profile, BP35C0)
        self.assertTrue(m.profile_forced)

    def test_confirm_switches_profile(self):
        from src.core.wisun import WiSunManager
        m = WiSunManager()
        m._confirm_profile_from_erxudp(True)
        self.assertIs(m.profile, BP35C0)
        self.assertTrue(m.profile_confirmed)
        # 2 回目以降は変えない
        m._confirm_profile_from_erxudp(False)
        self.assertIs(m.profile, BP35C0)

    def test_reply_uses_side_after_c0_erxudp(self):
        from src.core.wisun import WiSunManager

        async def main():
            m = WiSunManager()
            m.serial = FakeSerial(m, {})
            with mock.patch("src.core.wisun.wisun_echonet_ctrl.handle_packet", return_value=b"\x10\x81"):
                m._handle_serial_line(ERXUDP_C0)
                await asyncio.sleep(0.01)
            return m

        m = asyncio.run(main())
        sent = [c for c in m.serial.written if isinstance(c, bytes)]
        self.assertEqual(len(sent), 1)
        self.assertTrue(sent[0].startswith(b"SKSENDTO 1 FE80:0000:0000:0000:021D:1290:1234:5678 0E1A 1 0 0002 "))


if __name__ == "__main__":
    unittest.main()
