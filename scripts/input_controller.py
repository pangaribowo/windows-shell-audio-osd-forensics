"""
Input Controller: Win32 Synthetic Keyboard & Mouse Automation for AI Agents
Supports hotkeys (F1-F12, Volume Up/Down/Mute), mouse clicks, dragging, and unicode typing.
Requires desktop attachment (WinSta0\\Default) for background process safety.
"""

import time
import ctypes
from ctypes import wintypes
from scripts.screen_engine import attach_to_active_desktop, get_screen_metrics

user32 = ctypes.windll.user32

# Virtual Key constants
VK_MAP = {
    "f1": 0x70,
    "f2": 0x71,
    "f3": 0x72,
    "f4": 0x73,
    "f5": 0x74,
    "f6": 0x75,
    "f7": 0x76,
    "f8": 0x77,
    "f9": 0x78,
    "f10": 0x79,
    "f11": 0x7A,
    "f12": 0x7B,
    "f1_mute": 0xAD,
    "f2_vol": 0xAE,
    "f2_voldown": 0xAE,
    "f3_vol": 0xAF,
    "f3_volup": 0xAF,
    "volume_mute": 0xAD,
    "volumemute": 0xAD,
    "mute": 0xAD,
    "volume_down": 0xAE,
    "volumedown": 0xAE,
    "voldown": 0xAE,
    "volume_up": 0xAF,
    "volumeup": 0xAF,
    "volup": 0xAF,
    "enter": 0x0D,
    "return": 0x0D,
    "escape": 0x1B,
    "esc": 0x1B,
    "tab": 0x09,
    "space": 0x20,
    "backspace": 0x08,
    "shift": 0x10,
    "ctrl": 0x11,
    "control": 0x11,
    "alt": 0x12,
    "win": 0x5B,
    "windows": 0x5B,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
}

KEYEVENTF_EXTENDEDKEY = 0x0001
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004
KEYEVENTF_SCANCODE = 0x0008

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]

class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("u", INPUT_UNION),
    ]

INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
INPUT_HARDWARE = 2

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

def _send_input_safe(input_list):
    """
    Safely dispatch an array of INPUT structures via SendInput.
    Validates return value and automatically handles desktop re-attachment if needed.
    """
    attach_to_active_desktop()
    n = len(input_list)
    if n == 0:
        return True
    arr = (INPUT * n)(*input_list)
    ret = user32.SendInput(n, arr, ctypes.sizeof(INPUT))
    if ret == n:
        return True

    # If injection failed (e.g. desktop mismatch), try OpenInputDesktop directly
    err = ctypes.windll.kernel32.GetLastError()
    try:
        h_input = user32.OpenInputDesktop(0, False, 0x01FF)
        if h_input:
            if user32.SetThreadDesktop(h_input):
                ret2 = user32.SendInput(n, arr, ctypes.sizeof(INPUT))
                user32.CloseDesktop(h_input)
                if ret2 == n:
                    return True
            else:
                user32.CloseDesktop(h_input)
    except Exception:
        pass

    raise RuntimeError(f"SendInput dispatched {ret}/{n} inputs (Win32 LastError: {err})")

def press_key(key_name, hold_seconds=0.05):
    """
    Press and release a key by name or virtual key code.
    Example: press_key("f3"), press_key("volume_up")
    """
    attach_to_active_desktop()
    vk = None
    if isinstance(key_name, int):
        vk = key_name
    elif isinstance(key_name, str):
        key_clean = key_name.strip().lower()
        vk = VK_MAP.get(key_clean)
        if vk is None:
            if len(key_clean) == 1 and (key_clean.isalnum()):
                vk = user32.VkKeyScanW(ord(key_clean)) & 0xFF

    if vk is None:
        raise ValueError(f"Unsupported key name or code: {key_name}")

    scan = user32.MapVirtualKeyW(vk, 0)

    # Send key down
    inp_down = INPUT()
    inp_down.type = INPUT_KEYBOARD
    inp_down.u.ki.wVk = vk
    inp_down.u.ki.wScan = scan
    inp_down.u.ki.dwFlags = 0
    _send_input_safe([inp_down])

    if hold_seconds > 0:
        time.sleep(hold_seconds)

    # Send key up
    inp_up = INPUT()
    inp_up.type = INPUT_KEYBOARD
    inp_up.u.ki.wVk = vk
    inp_up.u.ki.wScan = scan
    inp_up.u.ki.dwFlags = KEYEVENTF_KEYUP
    _send_input_safe([inp_up])
    return True

def press_hotkey_combo(keys, hold_seconds=0.05):
    """
    Press a key combination (e.g. ['ctrl', 'alt', 't'] or ['win', 'd']).
    """
    attach_to_active_desktop()
    vks = []
    for k in keys:
        if isinstance(k, int):
            vks.append(k)
        elif isinstance(k, str):
            clean = k.strip().lower()
            vk = VK_MAP.get(clean) or (user32.VkKeyScanW(ord(clean)) & 0xFF if len(clean) == 1 else None)
            if vk:
                vks.append(vk)

    # Press down in order
    down_inputs = []
    for vk in vks:
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = user32.MapVirtualKeyW(vk, 0)
        inp.u.ki.dwFlags = 0
        down_inputs.append(inp)
    if down_inputs:
        _send_input_safe(down_inputs)

    if hold_seconds > 0:
        time.sleep(hold_seconds)

    # Release in reverse order
    up_inputs = []
    for vk in reversed(vks):
        inp = INPUT()
        inp.type = INPUT_KEYBOARD
        inp.u.ki.wVk = vk
        inp.u.ki.wScan = user32.MapVirtualKeyW(vk, 0)
        inp.u.ki.dwFlags = KEYEVENTF_KEYUP
        up_inputs.append(inp)
    if up_inputs:
        _send_input_safe(up_inputs)

    return True

def move_mouse(x, y):
    """Move mouse cursor to absolute coordinates (x, y)."""
    attach_to_active_desktop()
    left, top, w, h = get_screen_metrics()
    x = max(left, min(x, left + w - 1))
    y = max(top, min(y, top + h - 1))

    # Normalized 0..65535 coordinate system for MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    norm_x = int(((x - left) * 65535) / max(1, w - 1))
    norm_y = int(((y - top) * 65535) / max(1, h - 1))

    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi.dx = norm_x
    inp.u.mi.dy = norm_y
    inp.u.mi.dwFlags = MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK
    _send_input_safe([inp])
    return True

def click_mouse(x, y, button="left", double=False):
    """
    Click at (x, y) with specified mouse button ("left", "right", "middle").
    """
    attach_to_active_desktop()
    move_mouse(x, y)
    time.sleep(0.02)

    down_flag = MOUSEEVENTF_LEFTDOWN
    up_flag = MOUSEEVENTF_LEFTUP
    if button == "right":
        down_flag = MOUSEEVENTF_RIGHTDOWN
        up_flag = MOUSEEVENTF_RIGHTUP
    elif button == "middle":
        down_flag = MOUSEEVENTF_MIDDLEDOWN
        up_flag = MOUSEEVENTF_MIDDLEUP

    clicks = 2 if double else 1
    for _ in range(clicks):
        inp_down = INPUT()
        inp_down.type = INPUT_MOUSE
        inp_down.u.mi.dwFlags = down_flag
        _send_input_safe([inp_down])

        time.sleep(0.03)

        inp_up = INPUT()
        inp_up.type = INPUT_MOUSE
        inp_up.u.mi.dwFlags = up_flag
        _send_input_safe([inp_up])

        if double:
            time.sleep(0.05)

    return True

def type_text(text):
    """Type unicode text into the currently focused window."""
    attach_to_active_desktop()
    inputs = []
    for char in text:
        inp_down = INPUT()
        inp_down.type = INPUT_KEYBOARD
        inp_down.u.ki.wVk = 0
        inp_down.u.ki.wScan = ord(char)
        inp_down.u.ki.dwFlags = KEYEVENTF_UNICODE
        inputs.append(inp_down)

        inp_up = INPUT()
        inp_up.type = INPUT_KEYBOARD
        inp_up.u.ki.wVk = 0
        inp_up.u.ki.wScan = ord(char)
        inp_up.u.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
        inputs.append(inp_up)

    if inputs:
        _send_input_safe(inputs)
    return True
