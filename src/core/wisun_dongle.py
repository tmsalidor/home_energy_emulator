"""Wi-SUN ドングルの種類ごとの違いをまとめたモジュール。

対応しているドングル:
- skstack_a1: TESSERA RL7023 / ROHM BP35A1 などの SKSTACK IP (従来からの形式)
- bp35c0:     RATOC RS-WSUHA-P (ROHM BP35C0) などのデュアルスタック版 SKSTACK IP。
              ERXUDP / EVENT / SKSENDTO に SIDE (0 = Bルート) が加わる。

シリアルに依存しない純粋関数だけを置き、テストしやすくしている。
"""
from __future__ import annotations

import glob
import os
import re
from dataclasses import dataclass
from typing import Iterable, Optional


@dataclass(frozen=True)
class DongleProfile:
    name: str
    label: str
    has_side: bool          # ERXUDP / EVENT / SKSENDTO に SIDE が入るか
    side: str = "0"         # Bルートの SIDE 値
    check_payload_mode: bool = False  # 起動時に ROPT で受信データの形式を確かめるか


SKSTACK_A1 = DongleProfile(
    name="skstack_a1",
    label="SKSTACK IP (TESSERA RL7023 / ROHM BP35A1 形式)",
    has_side=False,
)
BP35C0 = DongleProfile(
    name="bp35c0",
    label="SKSTACK IP デュアルスタック (RATOC RS-WSUHA-P / ROHM BP35C0 形式)",
    has_side=True,
    check_payload_mode=True,
)

PROFILES = {p.name: p for p in (SKSTACK_A1, BP35C0)}
DONGLE_CHOICES = ["auto", *PROFILES.keys()]


def profile_by_name(name: str) -> Optional[DongleProfile]:
    return PROFILES.get((name or "").strip().lower())


# --- 起動時の当たり付け ---------------------------------------------------
# 実機の返答文字列で確かめて直す前提。判定の条件はここだけに置く。
# BP35C0 のデュアルスタック版ファームは EVER 1.5.x と報告されている (他の実装より)。
# BP35A1 / TESSERA は EVER 1.2.x 系。
_DUAL_STACK_MIN_EVER = (1, 5)


def _parse_ever(skver: Optional[str]) -> Optional[tuple[int, ...]]:
    if not skver:
        return None
    m = re.search(r"EVER\s+(\d+(?:\.\d+)*)", skver)
    if not m:
        return None
    return tuple(int(x) for x in m.group(1).split("."))


def guess_profile(skver: Optional[str], skappver: Optional[str] = None,
                  skinfo: Optional[str] = None) -> tuple[DongleProfile, str]:
    """SKVER / SKAPPVER / SKINFO の返答からドングルの種類を推定する。

    戻り値は (プロファイル, 判定理由)。確定は最初の ERXUDP の形で行う。
    """
    ever = _parse_ever(skver)
    if ever is not None and ever[:2] >= _DUAL_STACK_MIN_EVER:
        return BP35C0, f"SKVER={skver!r} (EVER >= 1.5)"
    if ever is not None:
        return SKSTACK_A1, f"SKVER={skver!r}"
    return SKSTACK_A1, "SKVER の返答なし (従来の形式とみなす)"


# --- 受信行の読み取り -----------------------------------------------------
@dataclass(frozen=True)
class ErxUdp:
    sender: str
    dest: str
    rport: str
    lport: str
    sender_lla: str
    secured: str
    side: Optional[str]     # SIDE なしの形式では None
    datalen: int
    data_hex: str

    @property
    def has_side(self) -> bool:
        return self.side is not None

    @property
    def is_hex_payload(self) -> bool:
        return len(self.data_hex) == self.datalen * 2 and bool(
            re.fullmatch(r"[0-9A-Fa-f]*", self.data_hex))


def parse_erxudp(line: str) -> Optional[ErxUdp]:
    """ERXUDP 行を読む。9 項目 (SIDE なし) と 10 項目 (SIDE あり) のどちらも受ける。

    ERXUDP <SENDER> <DEST> <RPORT> <LPORT> <SENDERLLA> <SECURED> [<SIDE>] <DATALEN> <DATA>
    """
    parts = line.split()
    if not parts or parts[0] != "ERXUDP":
        return None
    if len(parts) == 9:
        _, sender, dest, rport, lport, lla, sec, datalen, data = parts
        side = None
    elif len(parts) == 10:
        _, sender, dest, rport, lport, lla, sec, side, datalen, data = parts
    else:
        return None
    try:
        n = int(datalen, 16)
    except ValueError:
        return None
    return ErxUdp(sender, dest, rport, lport, lla, sec, side, n, data)


@dataclass(frozen=True)
class WiSunEvent:
    num: str
    sender: Optional[str]
    side: Optional[str]
    param: Optional[str]


def parse_event(line: str, profile: DongleProfile) -> Optional[WiSunEvent]:
    """EVENT 行を読む。

    SIDE なし: EVENT <NUM> <SENDER> [<PARAM>]
    SIDE あり: EVENT <NUM> <SENDER> <SIDE> [<PARAM>]
    """
    parts = line.split()
    if len(parts) < 2 or parts[0] != "EVENT":
        return None
    num = parts[1]
    sender = parts[2] if len(parts) > 2 else None
    rest = parts[3:]
    if profile.has_side:
        side = rest[0] if len(rest) > 0 else None
        param = rest[1] if len(rest) > 1 else None
    else:
        side = None
        param = rest[0] if len(rest) > 0 else None
    return WiSunEvent(num, sender, side, param)


# --- 送信コマンドの組み立て -----------------------------------------------
def build_sendto_header(profile: DongleProfile, ip: str, port: int, data_len: int,
                        secured: str = "1", handle: str = "1") -> bytes:
    """SKSENDTO の前半 (データ本体の直前まで) を組み立てる。データは生バイトで続けて書く。

    SIDE なし: SKSENDTO <HANDLE> <IP> <PORT> <SEC> <LEN> <DATA>
    SIDE あり: SKSENDTO <HANDLE> <IP> <PORT> <SEC> <SIDE> <LEN> <DATA>
    """
    fields = ["SKSENDTO", handle, ip, f"{port:04X}", secured]
    if profile.has_side:
        fields.append(profile.side)
    fields.append(f"{data_len:04X}")
    return (" ".join(fields) + " ").encode("ascii")


# --- デバイスパスの探索 ---------------------------------------------------
_CANDIDATE_PATTERNS = (
    "/dev/serial/by-id/*",
    "/dev/ttyUSB*",
    "/dev/ttyACM*",
    "/dev/cu.usbserial*",   # macOS
    "/dev/cu.usbmodem*",    # macOS
    "/dev/cu.SLAB_USBtoUART*",
)


def find_serial_candidates(patterns: Iterable[str] = _CANDIDATE_PATTERNS) -> list[str]:
    seen: set[str] = set()
    found: list[str] = []
    for pattern in patterns:
        for path in sorted(glob.glob(pattern)):
            real = os.path.realpath(path)
            if real in seen:
                continue
            seen.add(real)
            found.append(path)
    return found


def resolve_device_path(configured: str) -> tuple[str, Optional[str]]:
    """設定のパスがあればそのまま、なければ候補から最初のものを返す。

    戻り値は (使うパス, 補足メッセージ)。
    """
    if not configured or configured.upper().startswith("COM") or os.path.exists(configured):
        return configured, None
    candidates = find_serial_candidates()
    if candidates:
        return candidates[0], (f"{configured} が見つからないため {candidates[0]} を使います "
                               f"(候補: {', '.join(candidates)})")
    return configured, None
