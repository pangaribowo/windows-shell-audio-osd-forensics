"""
OSD Sync Engine: Audio Volume Control, OSD Diagnostics & Multi-Layered Visual Synchronizer
Solves the ThinkPad / Windows OSD desync issue (where volume changes but OSD stays stuck at '0').
"""

import sys
import time
import ctypes
import subprocess
import psutil
from scripts.screen_engine import attach_to_active_desktop
from scripts.input_controller import press_key

def get_audio_info():
    """Retrieve current Windows audio volume and mute state via WASAPI (pycaw)."""
    attach_to_active_desktop()
    info = {
        "available": False,
        "volume_pct": None,
        "is_muted": None,
        "device_name": None,
        "waveout_vol": None,
    }
    co_initialized = False
    try:
        try:
            ctypes.windll.ole32.CoInitialize(None)
            co_initialized = True
        except Exception:
            pass

        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        info["available"] = True
        info["device_name"] = getattr(speakers, 'FriendlyName', 'Default Speakers')

        if hasattr(speakers, 'volume_percent') and speakers.volume_percent is not None:
            info["volume_pct"] = round(float(speakers.volume_percent), 1)
        elif hasattr(speakers, 'EndpointVolume'):
            scalar = speakers.EndpointVolume.GetMasterVolumeLevelScalar()
            info["volume_pct"] = round(float(scalar * 100.0), 1)

        if hasattr(speakers, 'EndpointVolume'):
            info["is_muted"] = bool(speakers.EndpointVolume.GetMute())
    except Exception as e:
        info["error"] = str(e)
    finally:
        if co_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass

    # Also query legacy waveOut volume
    try:
        winmm = ctypes.windll.winmm
        vol = ctypes.c_ulong()
        if winmm.waveOutGetVolume(0, ctypes.byref(vol)) == 0:
            info["waveout_vol"] = hex(vol.value)
    except Exception:
        pass

    return info

def set_audio_volume(percent):
    """
    Set master volume scalar (0.0 to 100.0) via WASAPI and synchronize legacy waveOut volume.
    """
    attach_to_active_desktop()
    percent = max(0.0, min(100.0, float(percent)))
    co_initialized = False
    try:
        try:
            ctypes.windll.ole32.CoInitialize(None)
            co_initialized = True
        except Exception:
            pass

        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        scalar = percent / 100.0
        speakers.EndpointVolume.SetMasterVolumeLevelScalar(scalar, None)

        # Synchronize legacy waveOut volume (0..65535 per channel)
        try:
            raw_vol = int((percent / 100.0) * 0xFFFF)
            packed = (raw_vol & 0xFFFF) | ((raw_vol & 0xFFFF) << 16)
            ctypes.windll.winmm.waveOutSetVolume(0, packed)
        except Exception:
            pass

        return True
    except Exception as e:
        print(f"[Error] set_audio_volume failed: {e}", file=sys.stderr)
        return False
    finally:
        if co_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass

def toggle_audio_mute():
    """Toggle audio mute state via WASAPI."""
    attach_to_active_desktop()
    co_initialized = False
    try:
        try:
            ctypes.windll.ole32.CoInitialize(None)
            co_initialized = True
        except Exception:
            pass

        from pycaw.pycaw import AudioUtilities
        speakers = AudioUtilities.GetSpeakers()
        cur_mute = speakers.EndpointVolume.GetMute()
        speakers.EndpointVolume.SetMute(not cur_mute, None)
        return not cur_mute
    except Exception as e:
        print(f"[Error] toggle_audio_mute failed: {e}", file=sys.stderr)
        return False
    finally:
        if co_initialized:
            try:
                ctypes.windll.ole32.CoUninitialize()
            except Exception:
                pass

def get_osd_diagnostics():
    """
    Scan active processes for Lenovo ThinkPad Hotkey and OSD drivers.
    Identifies root cause of OSD desynchronization and returns health status.
    """
    attach_to_active_desktop()
    detected = []
    known_osd_names = {
        "tphkload.exe": "Lenovo ThinkPad Hotkey Features Driver",
        "tposd.exe": "Lenovo On-Screen Display Drawer",
        "shtctky.exe": "Lenovo Shortcut Key Helper",
        "syntpenh.exe": "Synaptics TouchPad OSD Helper",
        "syntphelper.exe": "Synaptics TouchPad Assistant",
        "lenovohotkeys.exe": "Modern Lenovo Hotkeys UWP App",
        "lenovovantageservice.exe": "Lenovo Vantage Background Service",
        "ibmsrv.exe": "Lenovo System Interface Foundation Service",
        "tpwsup.exe": "Lenovo ThinkPad Support Helper"
    }

    for p in psutil.process_iter(['pid', 'name', 'exe', 'create_time']):
        try:
            p_name = (p.info['name'] or '').lower()
            if p_name in known_osd_names:
                detected.append({
                    "name": p.info['name'],
                    "pid": p.info['pid'],
                    "exe": p.info['exe'],
                    "role": known_osd_names[p_name]
                })
        except Exception:
            pass

    has_tphkload = any(d['name'].lower() == 'tphkload.exe' for d in detected)
    has_tposd = any(d['name'].lower() == 'tposd.exe' for d in detected)

    return {
        "detected_processes": detected,
        "has_tphkload": has_tphkload,
        "has_tposd": has_tposd,
        "osd_owner_identified": "Lenovo ThinkPad Hotkeys (tphkload.exe / tposd.exe)" if has_tphkload else "Standard Windows Shell",
        "slider_zero_root_cause": (
            "Legacy Lenovo Hotkey driver (tphkload.exe / spkvol.dll) uses pre-Windows 10 legacy audio mixer APIs. "
            "On modern Windows 10 with Realtek WASAPI audio endpoints, COM mixer queries fail to bind to the active endpoint, "
            "causing spkvol.dll to report 0 to tposd.exe. The black vertical slider displays '0' even while Windows master "
            "volume and audio playback operate normally."
        ) if has_tphkload else "No legacy Lenovo OSD driver detected."
    }

_active_hud_proc = None

def trigger_synced_hud(duration=1.8, position="top_left"):
    """
    Spawn the standalone OSD HUD in an asynchronous background process.
    Guarantees no lag in the main server loop and immediate visual feedback.
    """
    global _active_hud_proc
    try:
        # Check if an existing HUD process is still alive and kill it to refresh immediately
        if _active_hud_proc and _active_hud_proc.poll() is None:
            try:
                _active_hud_proc.terminate()
            except Exception:
                pass

        audio = get_audio_info()
        vol = audio.get("volume_pct", 50.0) or 50.0
        muted = bool(audio.get("is_muted", False))
        dev = audio.get("device_name", "Speaker") or "Speaker"

        cmd = [
            sys.executable,
            "-m", "core.osd_hud",
            "--volume", str(vol),
            "--device", str(dev),
            "--duration", str(duration),
            "--pos", str(position)
        ]
        if muted:
            cmd.append("--muted")

        _active_hud_proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        return True
    except Exception as e:
        print(f"[Warn] trigger_synced_hud failed: {e}", file=sys.stderr)
        return False

def sync_volume_action(action="up", percent=None, trigger_hud=True):
    """
    Execute volume action, synchronize audio subsystem, pulse Windows flyout,
    and render synchronized Agent HUD overlay.
    """
    attach_to_active_desktop()

    if action == "up":
        # Send native VK_VOLUME_UP (triggers Windows native flyout)
        press_key("volume_up")
        time.sleep(0.08)
    elif action == "down":
        # Send native VK_VOLUME_DOWN (triggers Windows native flyout)
        press_key("volume_down")
        time.sleep(0.08)
    elif action == "mute":
        press_key("volume_mute")
        time.sleep(0.08)
    elif action == "set" and percent is not None:
        set_audio_volume(percent)
        # Pulse keys to wake native flyout without changing volume
        press_key("volume_up")
        press_key("volume_down")
        time.sleep(0.08)
    elif action == "f2":
        # ThinkPad Volume Down hotkey simulation (triggers volume_down & f2)
        press_key("f2")
        press_key("volume_down")
        time.sleep(0.08)
    elif action == "f3":
        # ThinkPad Volume Up hotkey simulation (triggers volume_up & f3)
        press_key("f3")
        press_key("volume_up")
        time.sleep(0.08)

    # Sync legacy waveOut
    cur = get_audio_info()
    if cur.get("volume_pct") is not None:
        try:
            raw_vol = int((cur["volume_pct"] / 100.0) * 0xFFFF)
            packed = (raw_vol & 0xFFFF) | ((raw_vol & 0xFFFF) << 16)
            ctypes.windll.winmm.waveOutSetVolume(0, packed)
        except Exception:
            pass

    if trigger_hud:
        trigger_synced_hud()

    return cur

def fix_osd_sync(restart_explorer=False):
    """
    Remediate OSD desynchronization:
    1. Synchronize waveOut with WASAPI.
    2. If buggy tposd.exe or tphkload.exe is running, kill it so it stops drawing the stuck '0' slider.
    3. If restart_explorer is True, restart Windows Explorer shell to rebind SndVolSSO.dll to active WASAPI endpoints.
    4. Trigger synchronized HUD with true audio level.
    """
    attach_to_active_desktop()
    actions_taken = []
    
    # 1. Sync waveOut
    audio = get_audio_info()
    if audio.get("volume_pct") is not None:
        try:
            raw_vol = int((audio["volume_pct"] / 100.0) * 0xFFFF)
            packed = (raw_vol & 0xFFFF) | ((raw_vol & 0xFFFF) << 16)
            ctypes.windll.winmm.waveOutSetVolume(0, packed)
            actions_taken.append(f"Synchronized legacy waveOut volume to {audio['volume_pct']}%")
        except Exception as e:
            actions_taken.append(f"waveOut sync error: {e}")

    # 2. Check for tposd.exe or tphkload.exe
    for p in psutil.process_iter(['pid', 'name']):
        try:
            pname = (p.info['name'] or '').lower()
            if pname in ('tposd.exe', 'tphkload.exe'):
                p.terminate()
                actions_taken.append(f"Terminated stuck {pname} (PID {p.info['pid']})")
        except Exception:
            pass

    # 3. Optional explorer restart to rebind SndVolSSO.dll
    if restart_explorer:
        try:
            for p in psutil.process_iter(['pid', 'name']):
                if (p.info['name'] or '').lower() == 'explorer.exe':
                    p.kill()
            actions_taken.append("Restarted Windows Explorer to rebind SndVolSSO.dll to active WASAPI endpoint")
        except Exception as e:
            actions_taken.append(f"Explorer restart error: {e}")

    # 4. Trigger clean HUD
    trigger_synced_hud(duration=2.5)
    actions_taken.append("Triggered real-time Agent HUD overlay with accurate WASAPI volume")

    return {
        "status": "success",
        "audio": get_audio_info(),
        "actions_taken": actions_taken
    }

