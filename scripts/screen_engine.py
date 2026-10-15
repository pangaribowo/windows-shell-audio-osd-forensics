"""
Screen Engine: Win32 GDI BitBlt + CAPTURBLT Screen Capture & Hierarchy Inspector
Handles active desktop attachment (WinSta0\\Default), zero handle leaks, and pixel analysis.
"""

import sys
import ctypes
import threading
from ctypes import wintypes
from PIL import Image

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
kernel32 = ctypes.windll.kernel32

# Configure Win32 API function signatures for 64-bit pointer safety
user32.OpenDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
user32.OpenDesktopW.restype = wintypes.HDESK

user32.SetThreadDesktop.argtypes = [wintypes.HDESK]
user32.SetThreadDesktop.restype = wintypes.BOOL

user32.CloseDesktop.argtypes = [wintypes.HDESK]
user32.CloseDesktop.restype = wintypes.BOOL

user32.GetThreadDesktop.argtypes = [wintypes.DWORD]
user32.GetThreadDesktop.restype = wintypes.HDESK

kernel32.GetCurrentThreadId.argtypes = []
kernel32.GetCurrentThreadId.restype = wintypes.DWORD

user32.GetDC.argtypes = [wintypes.HWND]
user32.GetDC.restype = wintypes.HDC

user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
user32.ReleaseDC.restype = ctypes.c_int

gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi32.CreateCompatibleDC.restype = wintypes.HDC

gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL

gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP

gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
gdi32.SelectObject.restype = wintypes.HGDIOBJ

gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
gdi32.DeleteObject.restype = wintypes.BOOL

gdi32.BitBlt.argtypes = [
    wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
    wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD
]
gdi32.BitBlt.restype = wintypes.BOOL

gdi32.GetPixel.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi32.GetPixel.restype = wintypes.COLORREF

gdi32.GetDIBits.argtypes = [
    wintypes.HDC,
    wintypes.HBITMAP,
    wintypes.UINT,
    wintypes.UINT,
    ctypes.c_void_p,
    ctypes.c_void_p,
    wintypes.UINT
]
gdi32.GetDIBits.restype = ctypes.c_int

user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND

user32.ChildWindowFromPointEx.argtypes = [wintypes.HWND, wintypes.POINT, wintypes.UINT]
user32.ChildWindowFromPointEx.restype = wintypes.HWND

# Thread-safe desktop attachment cache to avoid kernel handle leaks
_thread_local = threading.local()
_shared_desktop_handle = None
_desktop_lock = threading.Lock()

def get_shared_desktop_handle():
    """Retrieve or open the shared handle to the Default interactive desktop."""
    global _shared_desktop_handle
    with _desktop_lock:
        if _shared_desktop_handle is None:
            _shared_desktop_handle = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        return _shared_desktop_handle

def attach_to_active_desktop():
    """
    Attach calling thread to the interactive user desktop (WinSta0\\Default).
    Uses cached desktop handles to prevent kernel handle exhaustion.
    """
    if getattr(_thread_local, "desktop_attached", False):
        return True
    try:
        hdesk = get_shared_desktop_handle()
        if hdesk and user32.SetThreadDesktop(hdesk):
            _thread_local.desktop_attached = True
            return True
        direct_hdesk = user32.OpenDesktopW("Default", 0, False, 0x01FF)
        if direct_hdesk and user32.SetThreadDesktop(direct_hdesk):
            _thread_local.desktop_attached = True
            return True
    except Exception as e:
        print(f"[Warn] attach_to_active_desktop error: {e}", file=sys.stderr)
    return False

# BITMAP structures for GDI
class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ('biSize', wintypes.DWORD),
        ('biWidth', wintypes.LONG),
        ('biHeight', wintypes.LONG),
        ('biPlanes', wintypes.WORD),
        ('biBitCount', wintypes.WORD),
        ('biCompression', wintypes.DWORD),
        ('biSizeImage', wintypes.DWORD),
        ('biXPelsPerMeter', wintypes.LONG),
        ('biYPelsPerMeter', wintypes.LONG),
        ('biClrUsed', wintypes.DWORD),
        ('biClrImportant', wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [('bmiHeader', BITMAPINFOHEADER), ('bmiColors', wintypes.DWORD * 3)]

class CURSORINFO(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('flags', wintypes.DWORD),
        ('hCursor', wintypes.HICON),
        ('ptScreenPos', wintypes.POINT),
    ]

def get_screen_metrics():
    """Return virtual screen bounds (left, top, width, height)."""
    SM_XVIRTUALSCREEN = 76
    SM_YVIRTUALSCREEN = 77
    SM_CXVIRTUALSCREEN = 78
    SM_CYVIRTUALSCREEN = 79

    w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
    h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
    left = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
    top = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)

    if w <= 0 or h <= 0:
        w = user32.GetSystemMetrics(0)  # SM_CXSCREEN
        h = user32.GetSystemMetrics(1)  # SM_CYSCREEN
        left = 0
        top = 0

    return left, top, w, h

def capture_screen(include_cursor=True, crop=None):
    """
    Capture the active desktop using GDI BitBlt with CAPTURBLT flag.
    CAPTURBLT (0x40000000) captures layered, alpha-blended, and OSD windows.
    Strict resource lifecycle cleanup in try...finally blocks.
    """
    attach_to_active_desktop()
    left, top, w, h = get_screen_metrics()

    hdc_screen = user32.GetDC(0)
    if not hdc_screen:
        raise RuntimeError("Failed to acquire screen device context (GetDC failed)")

    try:
        hdc_mem = gdi32.CreateCompatibleDC(hdc_screen)
        if not hdc_mem:
            raise RuntimeError("Failed to create compatible memory DC")

        try:
            hbm = gdi32.CreateCompatibleBitmap(hdc_screen, w, h)
            if not hbm:
                raise RuntimeError("Failed to create compatible bitmap")

            try:
                old_hbm = gdi32.SelectObject(hdc_mem, hbm)

                SRCCOPY = 0x00CC0020
                CAPTURBLT = 0x40000000
                rop = SRCCOPY | CAPTURBLT

                gdi32.BitBlt(hdc_mem, 0, 0, w, h, hdc_screen, left, top, rop)

                # Optionally draw mouse cursor onto memory DC
                if include_cursor:
                    try:
                        ci = CURSORINFO()
                        ci.cbSize = ctypes.sizeof(CURSORINFO)
                        CURSOR_SHOWING = 0x00000001
                        if user32.GetCursorInfo(ctypes.byref(ci)):
                            if ci.flags & CURSOR_SHOWING and ci.hCursor:
                                user32.DrawIconEx(
                                    hdc_mem,
                                    ci.ptScreenPos.x - left,
                                    ci.ptScreenPos.y - top,
                                    ci.hCursor,
                                    0,
                                    0,
                                    0,
                                    0,
                                    0x0003  # DI_NORMAL
                                )
                    except Exception:
                        pass

                bmi = BITMAPINFO()
                bmi.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
                bmi.bmiHeader.biWidth = w
                bmi.bmiHeader.biHeight = -h  # Negative height = top-down DIB
                bmi.bmiHeader.biPlanes = 1
                bmi.bmiHeader.biBitCount = 32
                bmi.bmiHeader.biCompression = 0  # BI_RGB

                buf_size = w * h * 4
                buf = ctypes.create_string_buffer(buf_size)
                gdi32.GetDIBits(hdc_mem, hbm, 0, h, ctypes.byref(buf), ctypes.byref(bmi), 0)

            finally:
                gdi32.SelectObject(hdc_mem, old_hbm)
                gdi32.DeleteObject(hbm)
        finally:
            gdi32.DeleteDC(hdc_mem)
    finally:
        user32.ReleaseDC(0, hdc_screen)

    img = Image.frombuffer('RGBA', (w, h), buf, 'raw', 'BGRA', 0, 1)
    img = img.convert('RGB')

    if crop:
        cx, cy, cw, ch = crop
        cw = max(1, cw)
        ch = max(1, ch)
        cx = max(0, min(cx, w - 1))
        cy = max(0, min(cy, h - 1))
        x2 = min(cx + cw, w)
        y2 = min(cy + ch, h)
        if x2 > cx and y2 > cy:
            img = img.crop((cx, cy, x2, y2))

    return img

def inspect_point(x, y):
    """
    Inspect windows (top-level and child controls) and exact pixel color at (x, y).
    Returns pixel RGB/HEX, direct hit window, child controls, and covering windows.
    """
    attach_to_active_desktop()

    _, _, sw, sh = get_screen_metrics()
    x = max(0, min(x, sw - 1))
    y = max(0, min(y, sh - 1))

    # 1. Query exact pixel color
    pixel_info = {"r": 0, "g": 0, "b": 0, "hex": "#000000"}
    hdc = user32.GetDC(0)
    if hdc:
        try:
            pix = gdi32.GetPixel(hdc, x, y)
            if pix != 0xFFFFFFFF:
                r = pix & 0xFF
                g = (pix >> 8) & 0xFF
                b = (pix >> 16) & 0xFF
                pixel_info = {
                    "r": r,
                    "g": g,
                    "b": b,
                    "hex": f"#{r:02x}{g:02x}{b:02x}"
                }
        finally:
            user32.ReleaseDC(0, hdc)

    # 2. Query direct hit window via WindowFromPoint
    pt = wintypes.POINT(x, y)
    direct_hwnd = user32.WindowFromPoint(pt)
    direct_window = None
    if direct_hwnd and user32.IsWindow(direct_hwnd):
        direct_window = _format_window_info(direct_hwnd)

    # 3. Enumerate all top-level and child windows covering the coordinate
    results = []

    def enum_wnd(hwnd, lparam):
        if user32.IsWindow(hwnd) and user32.IsWindowVisible(hwnd):
            rect = (ctypes.c_long * 4)()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            l, t, r, b = rect[0], rect[1], rect[2], rect[3]
            if l <= x <= r and t <= y <= b:
                w_info = _format_window_info(hwnd)

                children = []
                def enum_child(chwnd, clparam):
                    if user32.IsWindow(chwnd) and user32.IsWindowVisible(chwnd):
                        crect = (ctypes.c_long * 4)()
                        user32.GetWindowRect(chwnd, ctypes.byref(crect))
                        cl, ct, cr, cb = crect[0], crect[1], crect[2], crect[3]
                        if cl <= x <= cr and ct <= y <= cb and chwnd != hwnd:
                            c_info = _format_window_info(chwnd)
                            children.append(c_info)
                    return True

                CHILDENUM = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
                user32.EnumChildWindows(hwnd, CHILDENUM(enum_child), 0)
                children.sort(key=lambda c: c["rect"]["width"] * c["rect"]["height"])
                w_info["children"] = children
                results.append(w_info)
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_int, ctypes.c_int)
    user32.EnumWindows(WNDENUMPROC(enum_wnd), 0)

    results.sort(key=lambda item: item["rect"]["width"] * item["rect"]["height"])

    return {
        "coordinate": {"x": x, "y": y},
        "pixel": pixel_info,
        "hit_window": direct_window,
        "windows": results
    }

def _format_window_info(hwnd):
    """Extract metadata for a specific HWND."""
    import psutil

    rect = (ctypes.c_long * 4)()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    l, t, r, b = rect[0], rect[1], rect[2], rect[3]

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    title_buf = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(hwnd, title_buf, 512)

    cls_buf = ctypes.create_unicode_buffer(512)
    user32.GetClassNameW(hwnd, cls_buf, 512)

    ex_style = user32.GetWindowLongW(hwnd, -20)  # GWL_EXSTYLE
    style = user32.GetWindowLongW(hwnd, -16)     # GWL_STYLE

    pname = "Unknown"
    pexe = "Unknown"
    try:
        p = psutil.Process(pid.value)
        pname = p.name()
        pexe = p.exe()
    except Exception:
        pass

    is_layered = bool(ex_style & 0x00080000)      # WS_EX_LAYERED
    is_topmost = bool(ex_style & 0x00000008)      # WS_EX_TOPMOST
    is_transparent = bool(ex_style & 0x00000020)  # WS_EX_TRANSPARENT

    return {
        "hwnd": hwnd,
        "pid": pid.value,
        "process_name": pname,
        "process_exe": pexe,
        "title": title_buf.value,
        "class_name": cls_buf.value,
        "rect": {"left": l, "top": t, "right": r, "bottom": b, "width": r - l, "height": b - t},
        "is_layered": is_layered,
        "is_topmost": is_topmost,
        "is_transparent": is_transparent,
        "style": hex(style),
        "ex_style": hex(ex_style)
    }
