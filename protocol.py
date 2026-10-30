"""MR STAR / GATT-DEMO command frames (reverse engineered; no device readback)."""
from __future__ import annotations
import colorsys

WRITE_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"


def power_frame(enabled: bool) -> bytes:
    return bytes([0xBC, 0x01, 0x01, int(enabled), 0x55])


def rgb_frame(rgb: tuple[int, int, int], hue_offset: int = 0) -> bytes:
    if len(rgb) != 3 or any(not 0 <= c <= 255 for c in rgb):
        raise ValueError("RGB components must be in range 0–255")
    h, s, _ = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    hue = (round(h * 360) + int(hue_offset)) % 360
    sat = round(s * 1000)
    return bytes([0xBC, 0x04, 0x06, hue >> 8, hue & 0xFF,
                  sat >> 8, sat & 0xFF, 0, 0, 0x55])


def brightness_to_raw(percent: int) -> int:
    """Convert GUI brightness percent to MR STAR's 16-bit dimming value.

    The Python mr-star-ble implementation uses int(1024 * brightness),
    brightness in [0.0, 1.0].  Thus 100% MUST send 0x0400, not 0x0064.
    This conversion is kept in one place to prevent regressions.
    """
    p = max(0, min(100, int(percent)))
    return (1024 * p) // 100


def brightness_frame(percent: int) -> bytes:
    value = brightness_to_raw(percent)
    return bytes([0xBC, 0x05, 0x06, value >> 8, value & 0xFF,
                  0, 0, 0, 0, 0x55])


def hex_to_rgb(code: str) -> tuple[int, int, int]:
    value = code.strip().lstrip("#")
    if len(value) != 6:
        raise ValueError("Enter a 6-digit HEX color, e.g. #22C55E")
    try:
        return tuple(int(value[i:i+2], 16) for i in (0, 2, 4))
    except ValueError as exc:
        raise ValueError("HEX can only contain 0–9 and A–F") from exc


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def matched_brightness(rgb: tuple[int, int, int], master_percent: int) -> int:
    """Approximate HSV value channel with the device's separate brightness 0..100.

    The lamp supports only Hue + Saturation in the color frame. The V component
    of an RGB HEX color is mapped to the device global dimmer. Result is not a
    guarantee of photometric color accuracy; actual output depends on LEDs.
    """
    if len(rgb) != 3 or any(not 0 <= x <= 255 for x in rgb):
        raise ValueError('Invalid RGB value')
    master_percent = max(0, min(100, int(master_percent)))
    if max(rgb) == 0 or master_percent == 0:
        return 0
    return max(3, round(max(rgb) / 255 * master_percent))


# Empirical workaround for MODI LIFE / GATT--DEMO firmware.
# The physical unit was reported bright at 98% but unexpectedly dim at
# 99% and 100% for pure R, G, B. Mixed colors were unaffected. This is
# NOT a proven limit of the overall MR STAR protocol or of all devices.
PRIMARY_RGB_SAFE_MAX_PERCENT = 98


def is_primary_rgb(rgb: tuple[int, int, int]) -> bool:
    """Pure R, G or B (including dimmed HEX variants), not mixed colors."""
    return len(rgb) == 3 and all(0 <= c <= 255 for c in rgb) and sum(c > 0 for c in rgb) == 1


def applied_brightness(rgb: tuple[int, int, int], master_percent: int,
                       primary_rgb_fix: bool = True) -> int:
    """The LED-level percentage actually sent via BLE.

    This preserves the 0..1024 mapping for every other color and for
    primaries below the observed failure range. UI values stay unchanged.
    """
    requested = matched_brightness(rgb, master_percent)
    if primary_rgb_fix and is_primary_rgb(rgb):
        return min(requested, PRIMARY_RGB_SAFE_MAX_PERCENT)
    return requested


def white_frame() -> bytes:
    """Dedicated white command found in community MR STAR protocol research."""
    return bytes.fromhex('BC 13 02 00 00 55')


def mode_frame(index: int) -> bytes:
    if not isinstance(index, int) or not 1 <= index <= 117:
        raise ValueError('Native effect index must be between 1 and 117')
    return bytes([0xBC, 0x06, 0x02, index // 255, index % 255, 0x55])


def speed_frame(value: int) -> bytes:
    v = max(0, min(100, int(value)))
    return bytes([0xBC, 0x08, 0x01, v, 0x55])


def direction_frame(forward: bool) -> bytes:
    return bytes([0xBC, 0x07, 0x01, 0x00 if forward else 0x01, 0x55])

# The names below are sourced from community reverse-engineering. Exact scene
# behavior may vary with the controller firmware and LED strip topology.
EFFECT_FAMILIES = {
    'Basic / Color': (1, 32),
    'Opening / Closing': (35, 44),
    'Light / Dark': (45, 54),
    'Running Water': (55, 62),
    'Flow': (63, 75),
    'Trailing': (76, 83),
    'Running / Chasing': (84, 117),
}
EFFECT_PRESETS = [
    ('Auto cycle', 1), ('Symphony', 2), ('Energy', 3),
    ('Color jump', 4), ('Strobe / Flash', 7), ('Smooth gradient', 10),
    ('Flutter', 26), ('RGB flutter', 27), ('Color brush', 29),
    ('Opening', 35), ('Light / dark transition', 45),
    ('Running water', 55), ('Color flow', 63),
    ('Trailing light', 76), ('Seven-color running', 91),
]
