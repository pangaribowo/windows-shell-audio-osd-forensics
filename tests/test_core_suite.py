"""
Automated Regression and Forensic Verification Suite
Validates Win32 desktop attachment, screen capture, SendInput, WASAPI/waveOut sync,
and HTTP streaming server endpoints.
"""

import sys
import os
import time
import unittest
import urllib.request
import json
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.screen_engine import (
    attach_to_active_desktop,
    get_screen_metrics,
    capture_screen,
    inspect_point
)
from scripts.input_controller import (
    press_key,
    click_mouse,
    type_text
)
from scripts.osd_sync import (
    get_audio_info,
    set_audio_volume,
    get_osd_diagnostics,
    fix_osd_sync,
    trigger_synced_hud
)
from scripts.server import ThreadingHTTPServer, AgentServerHandler

class TestWindowsShellAudioForensics(unittest.TestCase):

    def test_01_desktop_attachment(self):
        """Verify Win32 desktop attachment without handle leaks."""
        h1 = attach_to_active_desktop()
        h2 = attach_to_active_desktop()
        self.assertIsNotNone(h1)
        self.assertEqual(h1, h2)

    def test_02_screen_metrics(self):
        """Verify screen dimension detection."""
        vx, vy, vw, vh = get_screen_metrics()
        self.assertGreater(vw, 640)
        self.assertGreater(vh, 480)

    def test_03_gdi_capture(self):
        """Verify GDI BitBlt capture."""
        img = capture_screen(include_cursor=False)
        self.assertIsNotNone(img)
        self.assertGreater(img.width, 0)
        self.assertGreater(img.height, 0)

    def test_04_cropped_capture(self):
        """Verify regional screen capture."""
        img = capture_screen(crop=(50, 50, 100, 100))
        self.assertEqual(img.width, 100)
        self.assertEqual(img.height, 100)

    def test_05_point_inspection(self):
        """Verify pixel color and window hierarchy inspection."""
        res = inspect_point(60, 60)
        self.assertIn("pixel", res)
        self.assertIn("hex", res["pixel"])
        self.assertIn("windows", res)

    def test_06_wasapi_waveout_sync(self):
        """Verify WASAPI master scalar and legacy waveOut synchronization."""
        initial = get_audio_info()
        orig_vol = initial.get("volume_pct", 14.0) or 14.0

        success = set_audio_volume(15.0)
        self.assertTrue(success)
        after = get_audio_info()
        self.assertEqual(after.get("volume_pct"), 15.0)

        # Restore original safe volume
        set_audio_volume(orig_vol)

    def test_07_input_controller(self):
        """Verify synthetic input execution."""
        # Non-destructive test
        res = press_key("f2")
        self.assertTrue(res)

    def test_08_osd_diagnostics(self):
        """Verify OSD health scan."""
        diag = get_osd_diagnostics()
        self.assertIn("has_tphkload", diag)
        self.assertIn("osd_owner_identified", diag)

    def test_09_hud_spawn(self):
        """Verify background HUD process execution."""
        res = trigger_synced_hud(duration=0.5)
        self.assertTrue(res)

    def test_10_http_server(self):
        """Verify REST API and MJPEG server."""
        test_port = 8995
        server = ThreadingHTTPServer(("127.0.0.1", test_port), AgentServerHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        time.sleep(0.3)

        try:
            req = urllib.request.Request(f"http://127.0.0.1:{test_port}/api/info")
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                self.assertIn("system", data)
                self.assertIn("audio", data)
        finally:
            server.shutdown()
            server.server_close()

if __name__ == "__main__":
    unittest.main()
