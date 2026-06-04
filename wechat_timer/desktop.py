from __future__ import annotations

import ctypes
import sys


def is_workstation_locked() -> bool:
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    UOI_NAME = 2
    desktop = user32.OpenInputDesktop(0, False, 0x0100)
    if not desktop:
        return True

    try:
        needed = ctypes.c_uint(0)
        user32.GetUserObjectInformationW(desktop, UOI_NAME, None, 0, ctypes.byref(needed))
        buffer = ctypes.create_unicode_buffer(max(needed.value, 256))
        ok = user32.GetUserObjectInformationW(
            desktop,
            UOI_NAME,
            buffer,
            ctypes.sizeof(buffer),
            ctypes.byref(needed),
        )
        if not ok:
            return False
        return buffer.value.lower() != "default"
    finally:
        user32.CloseDesktop(desktop)

