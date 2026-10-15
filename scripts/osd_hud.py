"""
OSD HUD: Visual Real-time On-Screen Display HUD Overlay
Renders a modern, borderless, topmost volume HUD that synchronizes with true WASAPI audio state.
Bypasses legacy OEM OSD bugs (e.g. Lenovo ThinkPad tposd.exe stuck at '0').
"""

import sys
import time
import argparse
import tkinter as tk

def render_hud(volume_pct, is_muted=False, device_name="Speaker", duration=1.8, position="top_left"):
    """
    Render a modern semi-transparent floating OSD HUD on screen.
    Auto-dismisses after duration seconds.
    """
    root = tk.Tk()
    root.title("Antigravity OSD HUD")
    root.overrideredirect(True)
    root.attributes('-topmost', True)
    try:
        root.attributes('-alpha', 0.94)
    except Exception:
        pass

    # Styling
    bg_color = "#111827"       # Dark Slate
    accent_color = "#3b82f6"   # Electric Blue
    text_color = "#f3f4f6"
    muted_color = "#ef4444"    # Red when muted
    bar_bg = "#374151"

    root.configure(bg=bg_color)

    # Position calculation
    width = 300
    height = 76
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()

    if position == "top_left":
        x = 50
        y = 50
    elif position == "top_center":
        x = (screen_w - width) // 2
        y = 50
    elif position == "bottom_center":
        x = (screen_w - width) // 2
        y = screen_h - height - 80
    else:
        x = 50
        y = 50

    root.geometry(f"{width}x{height}+{x}+{y}")

    # Header frame: Icon, Title & Percentage
    header = tk.Frame(root, bg=bg_color)
    header.pack(fill="x", padx=16, pady=(10, 4))

    icon_char = "🔇" if is_muted else "🔊"
    status_text = "MUTED" if is_muted else f"{int(round(volume_pct))}%"
    display_color = muted_color if is_muted else accent_color

    lbl_icon = tk.Label(header, text=icon_char, font=("Segoe UI Emoji", 14), bg=bg_color, fg=display_color)
    lbl_icon.pack(side="left")

    lbl_title = tk.Label(header, text=f" Volume", font=("Segoe UI", 11, "bold"), bg=bg_color, fg=text_color)
    lbl_title.pack(side="left")

    lbl_val = tk.Label(header, text=status_text, font=("Segoe UI", 12, "bold"), bg=bg_color, fg=display_color)
    lbl_val.pack(side="right")

    # Progress bar canvas
    canvas_w = width - 32
    canvas_h = 10
    canvas = tk.Canvas(root, width=canvas_w, height=canvas_h, bg=bar_bg, highlightthickness=0)
    canvas.pack(padx=16, pady=(4, 6))

    if not is_muted and volume_pct > 0:
        fill_w = max(4, int((canvas_w * min(100.0, max(0.0, volume_pct))) / 100.0))
        canvas.create_rectangle(0, 0, fill_w, canvas_h, fill=accent_color, width=0)

    # Subtitle: Device info
    lbl_device = tk.Label(root, text=str(device_name)[:36], font=("Segoe UI", 8), bg=bg_color, fg="#9ca3af")
    lbl_device.pack(side="left", padx=16, pady=(0, 6))

    # Auto-destroy timer
    ms = int(duration * 1000)
    root.after(ms, root.destroy)

    # Bring to foreground
    root.lift()
    root.mainloop()

def main():
    parser = argparse.ArgumentParser(description="Standalone Agent OSD HUD")
    parser.add_argument("--volume", type=float, default=50.0, help="Volume percentage (0-100)")
    parser.add_argument("--muted", action="store_true", help="Audio is muted")
    parser.add_argument("--device", default="Speaker/HP (Realtek HD Audio)", help="Audio endpoint name")
    parser.add_argument("--duration", type=float, default=1.8, help="Display duration in seconds")
    parser.add_argument("--pos", default="top_left", choices=["top_left", "top_center", "bottom_center"])

    args = parser.parse_args()
    render_hud(
        volume_pct=args.volume,
        is_muted=args.muted,
        device_name=args.device,
        duration=args.duration,
        position=args.pos
    )

if __name__ == "__main__":
    main()
