from __future__ import annotations

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path


def process_image_name(pid: int) -> str:
    if sys.platform != "win32" or pid <= 0:
        return ""

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""

    try:
        size = wintypes.DWORD(32768)
        buffer = ctypes.create_unicode_buffer(size.value)
        ok = kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size))
        return buffer.value if ok else ""
    finally:
        kernel32.CloseHandle(handle)


def activate_window_handle(handle: int) -> bool:
    if sys.platform != "win32" or handle <= 0:
        return False

    SW_RESTORE = 9
    user32 = ctypes.windll.user32
    if user32.IsIconic(handle):
        user32.ShowWindow(handle, SW_RESTORE)
    foreground = user32.GetForegroundWindow()
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None) if foreground else 0
    target_thread = user32.GetWindowThreadProcessId(handle, None)
    current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
    attached_foreground = False
    attached_target = False
    try:
        if foreground_thread and foreground_thread != current_thread:
            attached_foreground = bool(user32.AttachThreadInput(current_thread, foreground_thread, True))
        if target_thread and target_thread != current_thread:
            attached_target = bool(user32.AttachThreadInput(current_thread, target_thread, True))
        user32.BringWindowToTop(handle)
        user32.SetForegroundWindow(handle)
        user32.SetFocus(handle)
        return user32.GetForegroundWindow() == handle
    finally:
        if attached_target:
            user32.AttachThreadInput(current_thread, target_thread, False)
        if attached_foreground:
            user32.AttachThreadInput(current_thread, foreground_thread, False)


def find_top_level_window_handle(
    process_names: list[str],
    class_names: list[str],
    titles: list[str],
) -> int:
    if sys.platform != "win32":
        return 0

    expected_processes = {name.lower() for name in process_names}
    expected_classes = {name.lower() for name in class_names}
    expected_titles = {name.lower() for name in titles}
    user32 = ctypes.windll.user32
    matches: list[int] = []
    callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @callback_type
    def callback(hwnd, _lparam):
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = Path(process_image_name(pid.value)).name.lower()
        if process_name not in expected_processes:
            return True

        class_buffer = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buffer, 256)
        if class_buffer.value.lower() not in expected_classes:
            return True

        text_length = user32.GetWindowTextLengthW(hwnd)
        title_buffer = ctypes.create_unicode_buffer(text_length + 1)
        user32.GetWindowTextW(hwnd, title_buffer, text_length + 1)
        if title_buffer.value.lower() not in expected_titles:
            return True

        matches.append(int(hwnd))
        return False

    user32.EnumWindows(callback, 0)
    return matches[0] if matches else 0


def post_window_click(handle: int, screen_x: int, screen_y: int) -> bool:
    if sys.platform != "win32" or handle <= 0:
        return False

    WM_MOUSEMOVE = 0x0200
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP = 0x0202
    MK_LBUTTON = 0x0001
    user32 = ctypes.windll.user32
    point = wintypes.POINT(screen_x, screen_y)
    if not user32.ScreenToClient(handle, ctypes.byref(point)):
        return False
    lparam = (point.y << 16) | (point.x & 0xFFFF)
    user32.PostMessageW(handle, WM_MOUSEMOVE, 0, lparam)
    user32.PostMessageW(handle, WM_LBUTTONDOWN, MK_LBUTTON, lparam)
    user32.PostMessageW(handle, WM_LBUTTONUP, 0, lparam)
    return True


def post_window_text(handle: int, text: str) -> bool:
    if sys.platform != "win32" or handle <= 0 or not text:
        return False

    WM_CHAR = 0x0102
    user32 = ctypes.windll.user32
    for character in text:
        if not user32.PostMessageW(handle, WM_CHAR, ord(character), 1):
            return False
    return True


def post_window_wheel(handle: int, screen_x: int, screen_y: int, wheel_delta: int) -> bool:
    if sys.platform != "win32" or handle <= 0:
        return False

    WM_MOUSEWHEEL = 0x020A
    user32 = ctypes.windll.user32
    wparam = (wheel_delta & 0xFFFF) << 16
    lparam = ((screen_y & 0xFFFF) << 16) | (screen_x & 0xFFFF)
    return bool(user32.PostMessageW(handle, WM_MOUSEWHEEL, wparam, lparam))
