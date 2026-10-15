"""
CLI Entry Point for Autonomous Debugger Agent Core
"""

import sys
import os
import argparse

# Add repository root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.screen_engine import capture_screen, inspect_point
from scripts.input_controller import press_key, click_mouse, type_text
from scripts.osd_sync import (
    get_audio_info,
    get_osd_diagnostics,
    sync_volume_action,
    fix_osd_sync,
    trigger_synced_hud
)
from scripts.server import run_server

def main():
    parser = argparse.ArgumentParser(
        description="Autonomous Debugger Agent - Desktop Computer-Use Core"
    )
    subparsers = parser.add_subparsers(dest="command")

    # Command: serve
    serve_p = subparsers.add_parser("serve", help="Start the live HTTP streaming and agent server")
    serve_p.add_argument("-p", "--port", type=int, default=8088, help="Port to listen on (default: 8088)")
    serve_p.add_argument("--host", default="127.0.0.1", help="Host interface (default: 127.0.0.1)")
    serve_p.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")

    # Command: snapshot
    snap_p = subparsers.add_parser("snapshot", help="Capture a desktop screenshot and save to disk")
    snap_p.add_argument("-o", "--output", default="desktop_snapshot.png", help="Output file path")
    snap_p.add_argument("--crop", nargs=4, type=int, metavar=("X", "Y", "W", "H"), help="Crop region")
    snap_p.add_argument("--no-cursor", action="store_true", help="Exclude mouse cursor")

    # Command: inspect
    insp_p = subparsers.add_parser("inspect", help="Inspect window hierarchy and pixel at (x, y)")
    insp_p.add_argument("x", type=int, help="X coordinate")
    insp_p.add_argument("y", type=int, help="Y coordinate")

    # Command: press
    press_p = subparsers.add_parser("press", help="Send synthetic hotkey (e.g. f2, f3, volume_up)")
    press_p.add_argument("key", help="Key name (f2, f3, volume_up, volume_down, mute, etc.)")

    # Command: sync-osd
    sync_p = subparsers.add_parser("sync-osd", help="Remediate Lenovo stuck '0' slider and sync WASAPI & waveOut")
    sync_p.add_argument("--restart-explorer", action="store_true", help="Restart Windows Explorer to rebind SndVolSSO.dll")

    # Command: hud
    hud_p = subparsers.add_parser("hud", help="Render synchronized floating OSD HUD")
    hud_p.add_argument("--duration", type=float, default=2.0, help="HUD duration in seconds")

    args = parser.parse_args()

    if args.command == "serve" or args.command is None:
        port = getattr(args, "port", 8088)
        host = getattr(args, "host", "127.0.0.1")
        no_browser = getattr(args, "no_browser", False)
        run_server(host=host, port=port, open_browser=not no_browser)

    elif args.command == "snapshot":
        crop = getattr(args, "crop", None)
        cursor = not getattr(args, "no_cursor", False)
        img = capture_screen(include_cursor=cursor, crop=crop)
        out_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        img.save(out_path)
        print(f"[✓] Screenshot saved to: {out_path} ({img.width}x{img.height})")

    elif args.command == "inspect":
        res = inspect_point(args.x, args.y)
        pix = res.get("pixel", {})
        print(f"[+] Pixel Color: {pix.get('hex', 'N/A')} (RGB {pix.get('r')}, {pix.get('g')}, {pix.get('b')})")
        hit = res.get("hit_window")
        if hit:
            print(f"[+] Direct Hit: HWND {hit['hwnd']} | Class: '{hit['class_name']}' | Title: '{hit['title']}' | PID: {hit['pid']} ({hit['process_name']})")
        w_list = res.get("windows", [])
        print(f"[+] Covering Windows ({len(w_list)}):")
        for idx, item in enumerate(w_list[:5], 1):
            print(f"[{idx}] HWND: {item['hwnd']} | PID: {item['pid']} ({item['process_name']}) | Class: '{item['class_name']}' | Rect: {item['rect']}")

    elif args.command == "press":
        print(f"[*] Dispatching key: {args.key}...")
        press_key(args.key)
        print("[✓] Key sent.")

    elif args.command == "sync-osd":
        print("[*] Running OSD synchronization remediation...")
        restart_exp = getattr(args, "restart_explorer", False)
        report = fix_osd_sync(restart_explorer=restart_exp)
        print(f"[✓] Status: {report['status']}")
        for a in report["actions_taken"]:
            print(f"  - {a}")
        audio = report["audio"]
        print(f"[+] Active Volume: {audio.get('volume_pct')}% (Muted: {audio.get('is_muted')})")

    elif args.command == "hud":
        trigger_synced_hud(duration=args.duration)
        print(f"[✓] HUD triggered ({args.duration}s).")

if __name__ == "__main__":
    main()
