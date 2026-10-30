# Lab Beacon Demo 1.0.3

Standalone Python/Tkinter demonstration for a Windows lab: attach to an existing CANoe instance, monitor its Measurement.Running state and configurable alarm System Variables, and drive an MR STAR / GATT--DEMO BLE lamp.

| Priority | Alarm | Color | Default |
|---|---|---|---|
| 1 | Error (latched until acknowledged) | #FF0000 | Blink |
| 2 | Chamber DI water low | #00FFFF | Blink |
| 3 | Low disk space | #FFFF00 | Blink |
| 4 | CANoe running | #00FF00 | Solid |

Per-alarm enable, Solid/Blink and ON/OFF duration (250–3000 ms) are configurable. Normal Stop and Unknown request lamp OFF. Error detection and DI water require explicit System Variable mapping, disabled by default. Error > Water > Disk > Running. Polling cannot guarantee detection of short error pulses: hold the source until observed, including before Stop.

Portable Windows package: extract the entire ZIP and double-click Lab_Beacon_Demo.exe; keep _internal next to it. No target-machine Python/BAT installation is required. The application requests asInvoker privileges. Save a CANoe diagnostic report from Debug / Test. For source users only: run INSTALL_WINDOWS.bat, then RUN_WINDOWS.bat. Python 3.11+ with Tk and Windows Bluetooth required. RUN_SIMULATED_LED.bat runs without a physical lamp; Debug buttons test every color without CANoe. CANoe reads are isolated in a subprocess; attach-only COM never launches or stops CANoe. Settings persist under %LOCALAPPDATA%\LabBeaconDemo.

Read [README_TH.md](README_TH.md) for complete setup, configuration, CAPL integration, limitations, credits and Windows acceptance checks. Windows EXE builds run on GitHub Actions with a packaged GUI/simulated BLE smoke test. Live CANoe and physical BLE validation remain pending.

Validation: `python -m unittest discover -s tests -v` (20 tests), Python compile and import. See [VALIDATION.md](VALIDATION.md).

Based on [TOPTUBBY/Python-MR_STAR_RGB_Controller](https://github.com/TOPTUBBY/Python-MR_STAR_RGB_Controller) (MIT). Protocol reference credit: [labsensacional/mrstar-ble-light](https://github.com/labsensacional/mrstar-ble-light). See LICENSE and README_TH.md for details.

1.0.1 adds attach-only Running Object Table discovery and DIAGNOSE_CANOE.bat for 0x800401E3 troubleshooting. Use the same Windows user/elevation for CANoe and Beacon. ROT fallback cannot bypass Windows permissions or restore missing COM registration.

1.0.2 validates the Python interpreter and dependencies before launching. INSTALL_WINDOWS.bat preserves a broken .venv as .venv_backup_* and recreates it with a working local 64-bit Python, preferring 3.13. This repairs missing base-interpreter paths; it does not establish that the separate CANoe COM issue is resolved. New batch files have been reviewed but not executed on Windows here.
