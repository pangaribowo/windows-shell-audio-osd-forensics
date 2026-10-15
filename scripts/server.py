"""
Server: Threaded HTTP Streaming & REST API Server for AI Agents
Provides real-time MJPEG video stream (/api/stream), snapshot, crop, inspection,
and computer-use action endpoints (/api/action/*) for autonomous agents and web clients.
"""

import sys
import io
import time
import json
import socket
import webbrowser
import threading
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from scripts.screen_engine import (
    get_screen_metrics,
    capture_screen,
    inspect_point,
    attach_to_active_desktop
)
from scripts.input_controller import (
    press_key,
    press_hotkey_combo,
    click_mouse,
    move_mouse,
    type_text
)
from scripts.osd_sync import (
    get_audio_info,
    set_audio_volume,
    toggle_audio_mute,
    get_osd_diagnostics,
    trigger_synced_hud,
    sync_volume_action,
    fix_osd_sync
)
from scripts.web_ui import HTML_PAGE

class AgentServerHandler(BaseHTTPRequestHandler):
    """Multi-threaded HTTP handler with streaming and REST API."""

    def log_message(self, format, *args):
        # Suppress noisy GET requests for high-frequency streaming
        first_arg = str(args[0]) if args else ""
        if "/api/stream" in first_arg or "/api/screenshot" in first_arg:
            return
        super().log_message(format, *args)

    def send_json(self, status_code, data):
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        attach_to_active_desktop()
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif path == "/api/stream":
            # Realtime MJPEG live stream
            try:
                fps = 15
                if "fps" in query:
                    try:
                        fps = max(1, min(30, int(query["fps"][0])))
                    except Exception:
                        pass
                delay = 1.0 / fps

                crop = None
                if "crop" in query:
                    try:
                        parts = [int(p) for p in query["crop"][0].split(",")]
                        if len(parts) == 4:
                            crop = tuple(parts)
                    except Exception:
                        pass

                self.send_response(200)
                self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Pragma", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                attach_to_active_desktop()
                while True:
                    t_start = time.time()
                    img = capture_screen(include_cursor=True, crop=crop)
                    bio = io.BytesIO()
                    img.save(bio, format="JPEG", quality=75)
                    frame_bytes = bio.getvalue()

                    header = (
                        b"--frame\r\n"
                        b"Content-Type: image/jpeg\r\n"
                        b"Content-Length: " + str(len(frame_bytes)).encode("ascii") + b"\r\n\r\n"
                    )
                    self.wfile.write(header)
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b"\r\n")

                    elapsed = time.time() - t_start
                    sleep_time = max(0.01, delay - elapsed)
                    time.sleep(sleep_time)

            except (BrokenPipeError, ConnectionResetError):
                pass
            except Exception as e:
                print(f"[Stream error] {e}", file=sys.stderr)
            return

        elif path == "/api/screenshot":
            try:
                fmt = query.get("format", ["jpeg"])[0].upper()
                if fmt not in ("JPEG", "PNG"):
                    fmt = "JPEG"
                cursor = query.get("cursor", ["true"])[0].lower() != "false"

                img = capture_screen(include_cursor=cursor)
                bio = io.BytesIO()
                if fmt == "PNG":
                    img.save(bio, format="PNG")
                    content_type = "image/png"
                else:
                    img.save(bio, format="JPEG", quality=82)
                    content_type = "image/jpeg"

                data = bio.getvalue()
                self.send_response(200)
                self.send_header("Content-Type", content_type)
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/crop":
            try:
                _, _, sw, sh = get_screen_metrics()
                x = int(query.get("x", [0])[0])
                y = int(query.get("y", [0])[0])
                w = int(query.get("w", [300])[0])
                h = int(query.get("h", [300])[0])

                w = max(1, min(w, sw))
                h = max(1, min(h, sh))
                x = max(0, min(x, sw - 1))
                y = max(0, min(y, sh - 1))

                img = capture_screen(include_cursor=True, crop=(x, y, w, h))
                bio = io.BytesIO()
                img.save(bio, format="PNG")
                data = bio.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "image/png")
                self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/inspect":
            try:
                x = int(query.get("x", [0])[0])
                y = int(query.get("y", [0])[0])
                results = inspect_point(x, y)
                self.send_json(200, results)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/info":
            try:
                import platform
                _, _, sw, sh = get_screen_metrics()
                audio = get_audio_info()
                osd = get_osd_diagnostics()
                payload = {
                    "system": {
                        "os": f"Windows {platform.release()}",
                        "machine": platform.machine(),
                        "processor": platform.processor()
                    },
                    "screen": {"w": sw, "h": sh},
                    "audio": audio,
                    "osd": osd,
                    "timestamp": time.time()
                }
                self.send_json(200, payload)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

    def do_POST(self):
        attach_to_active_desktop()
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length) if content_length > 0 else b"{}"
        try:
            payload = json.loads(post_data.decode("utf-8")) if post_data else {}
        except Exception:
            payload = {}

        if path == "/api/action/hotkey":
            key = payload.get("key")
            if not key:
                self.send_json(400, {"error": "Missing 'key' in request body"})
                return
            try:
                press_key(key)
                self.send_json(200, {"status": "success", "key": key})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/action/volume":
            action = payload.get("action", "up")
            percent = payload.get("percent")
            trigger_hud = payload.get("trigger_hud", True)
            try:
                result_audio = sync_volume_action(action=action, percent=percent, trigger_hud=trigger_hud)
                self.send_json(200, {"status": "success", "action": action, "audio": result_audio})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/action/click":
            x = payload.get("x")
            y = payload.get("y")
            button = payload.get("button", "left")
            double = payload.get("double", False)
            if x is None or y is None:
                self.send_json(400, {"error": "Missing 'x' or 'y' coordinate"})
                return
            try:
                click_mouse(int(x), int(y), button=button, double=bool(double))
                self.send_json(200, {"status": "success", "x": x, "y": y, "button": button})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/action/type":
            text = payload.get("text", "")
            try:
                type_text(text)
                self.send_json(200, {"status": "success", "length": len(text)})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/action/fix_osd":
            try:
                restart_explorer = bool(payload.get("restart_explorer", False))
                report = fix_osd_sync(restart_explorer=restart_explorer)
                self.send_json(200, report)
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        elif path == "/api/action/hud":
            duration = payload.get("duration", 1.8)
            pos = payload.get("pos", "top_left")
            try:
                trigger_synced_hud(duration=duration, position=pos)
                self.send_json(200, {"status": "success", "duration": duration, "pos": pos})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not Found")

def run_server(host="127.0.0.1", port=8088, open_browser=True, max_retries=10):
    ThreadingHTTPServer.allow_reuse_address = True
    server = None
    current_port = port
    for _ in range(max_retries):
        try:
            server = ThreadingHTTPServer((host, current_port), AgentServerHandler)
            break
        except OSError as e:
            if "10048" in str(e) or "Address already in use" in str(e):
                current_port += 1
            else:
                raise
    if server is None:
        raise RuntimeError(f"Could not bind to any port from {port} to {current_port - 1}")

    server.daemon_threads = True
    url = f"http://{host}:{current_port}/"
    print(f"[+] Antigravity Desktop Agent Core running at {url}")
    print(f"[+] Live Stream endpoint: {url}api/stream")
    print(f"[+] AI Agent Action endpoint: {url}api/action/*")
    print(f"[+] Press Ctrl+C to terminate.")

    if open_browser:
        def _launch():
            time.sleep(0.4)
            try:
                webbrowser.open(url)
            except Exception:
                pass
        threading.Thread(target=_launch, daemon=True).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Server stopped by user.")
    finally:
        server.server_close()
