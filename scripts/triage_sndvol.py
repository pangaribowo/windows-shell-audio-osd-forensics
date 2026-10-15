"""
Windows Shell SndVolSSO / DirectUI OSD Forensics Utility
Traces the NativeHWNDHost -> TouchHWNDElement -> TouchSlider UI Automation hierarchy
and verifies whether SndVolSSO.dll is accurately bound to active WASAPI endpoints.
"""

import sys
import os
import time
import ctypes
from ctypes import wintypes
import psutil

# Add repository root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.screen_engine import attach_to_active_desktop
from scripts.input_controller import press_key
from scripts.osd_sync import get_audio_info

def run_triage(pulse_volume=True):
    attach_to_active_desktop()
    print("=" * 65)
    print(" WINDOWS SHELL SndVolSSO.dll / DirectUI OSD FORENSIC TRIAGE")
    print("=" * 65)

    audio = get_audio_info()
    print(f"[*] Active Audio Device : {audio.get('device_name')}")
    print(f"[*] WASAPI Master Vol   : {audio.get('volume_pct')}% (Muted: {audio.get('is_muted')})")
    print(f"[*] Legacy waveOut Vol  : {audio.get('waveout_vol')}")

    if pulse_volume:
        print("[*] Pulsing VK_VOLUME_UP to trigger Windows Shell OSD popup...")
        press_key("volume_up")
        time.sleep(0.12)

    user32 = ctypes.windll.user32
    pt = wintypes.POINT(82, 160)
    hwnd = user32.WindowFromPoint(pt)
    if not hwnd:
        print("[-] No window detected at screen coordinate (82, 160). OSD may be hidden.")
        return

    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    cls_name = buf.value
    rect = wintypes.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))

    print(f"\n[+] Hit Window at (82, 160):")
    print(f"    HWND       : {hwnd}")
    print(f"    Class Name : '{cls_name}'")
    print(f"    Bounds     : Left={rect.left}, Top={rect.top}, Right={rect.right}, Bottom={rect.bottom} [{rect.right-rect.left}x{rect.bottom-rect.top}]")

    # Parent chain
    parent = user32.GetParent(hwnd)
    if parent:
        user32.GetClassNameW(parent, buf, 256)
        p_cls = buf.value
        user32.GetWindowRect(parent, ctypes.byref(rect))
        print(f"[+] Parent Window:")
        print(f"    HWND       : {parent}")
        print(f"    Class Name : '{p_cls}'")
        print(f"    Bounds     : Left={rect.left}, Top={rect.top}, Right={rect.right}, Bottom={rect.bottom}")

    # UI Automation Dump
    try:
        import uiautomation as auto
        target = parent if parent else hwnd
        elem = auto.ControlFromHandle(target)
        print(f"\n[+] UI Automation Tree Structure (Target HWND: {target}):")
        def walk(ctrl, depth=1):
            indent = "  " * depth
            name = getattr(ctrl, 'Name', '')
            c_type = getattr(ctrl, 'ControlTypeName', '')
            c_cls = getattr(ctrl, 'ClassName', '')
            val = ""
            try:
                val = ctrl.GetLegacyIAccessiblePattern().Value
            except:
                pass
            print(f"{indent}└── [{c_type}] Name='{name}' Class='{c_cls}' Value='{val}'")
            for c in ctrl.GetChildren():
                walk(c, depth + 1)
        walk(elem)
    except Exception as e:
        print(f"[-] UI Automation inspection note: {e}")

    print("\n[✓] Forensic triage completed.")

if __name__ == "__main__":
    run_triage()
