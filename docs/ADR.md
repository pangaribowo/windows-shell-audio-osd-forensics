# Architectural Decision Records (ADR)

## ADR-001: Shell Refresh vs. Process Memory Injection for SndVolSSO.dll COM Re-binding

### Status
Accepted

### Context
When the Windows Sound Volume Shell Service Object (`SndVolSSO.dll`) inside `explorer.exe` loses its COM callback (`IAudioEndpointVolumeCallback`) to the active WASAPI render endpoint, it displays a static value of `0`. Two engineering strategies were evaluated to restore synchronization:
1. **Option A**: DLL injection / Detours hooking into `explorer.exe` to re-instantiate `CVolumeCallback`.
2. **Option B**: Clean shell cycle (`Stop-Process -Name explorer -Force`) with automated re-binding on launch.

### Decision
We adopted **Option B (Clean Shell Cycle)**.

### Consequences
- **Positive**: Zero risk of triggering Windows Defender anti-tamper heuristics or shell instability. Completely reproducible across standard user permissions without kernel debugging privileges.
- **Negative**: Brief desktop taskbar refresh (duration $\approx 850\text{ ms}$). Running user applications (Brave, VS Code, Python background daemons) are unaffected.

---

## ADR-002: WMI BIOS NVRAM Configuration vs. Software Keyboard Filter Drivers

### Status
Accepted

### Context
ThinkPad hardware volume keys (F2/F3) reverted to standard function keys upon system restart because the Embedded Controller was configured with `FnKeyAsPrimary,Disable`.

### Decision
We chose to modify and commit the BIOS NVRAM parameter via the Lenovo WMI provider (`root\wmi:Lenovo_SetBiosSetting` and `Lenovo_SaveBiosSettings`) rather than installing an OS-level keyboard filter driver or third-party hotkey remap software.

### Consequences
- **Positive**: Hardware-native persistence that operates independently of the OS, survives power drops, and introduces zero background CPU overhead.
- **Negative**: Requires Lenovo WMI provider support (universal across ThinkPad line).

---

## ADR-003: GDI BitBlt with Thread Desktop Attachment vs. DXGI Desktop Duplication API

### Status
Accepted

### Context
Autonomous AI agents require continuous desktop video capture and coordinate inspection. We evaluated DirectX Graphics Infrastructure (DXGI Desktop Duplication) versus Win32 GDI `BitBlt` with `CAPTURBLT`.

### Decision
We selected **GDI BitBlt with Thread Desktop Attachment (`OpenDesktopW / SetThreadDesktop`)**.

### Consequences
- **Positive**: Universal compatibility across headless/virtualized sessions, RDP connections, and hardware GPU sleep states. DXGI frequently errors with `DXGI_ERROR_ACCESS_LOST` when display topology or power state shifts.
- **Performance**: Capable of 15–30 FPS at 1366x768 with $< 1.5\%$ CPU overhead.

---

## ADR-004: Dual-Layer Audio Synchronization (WASAPI + Legacy waveOut)

### Status
Accepted

### Context
Modern Windows applications interact via WASAPI (`IAudioEndpointVolume`), while legacy Win32 utilities and game engines read the master volume register via `winmm.waveOutGetVolume()`.

### Decision
The synchronizer engine in `scripts/osd_sync.py` simultaneously reads/writes WASAPI scalars and synchronizes the 32-bit packed stereo register (`(left & 0xFFFF) | ((right & 0xFFFF) << 16)`) via `waveOutSetVolume`.

### Consequences
- **Positive**: Eliminates split-brain volume state between modern browser sessions and legacy Win32 tools.
- **Negative**: Negligible latency addition ($\approx 0.1\text{ ms}$).
