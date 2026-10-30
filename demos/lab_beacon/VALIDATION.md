# Validation — 1.0.2-demo

Date: 2026-10-30 (Asia/Bangkok).

## Completed in development environment

- Python 3.12 compile: all source and tests.
- Import: app / tkinter / BLE manager / policy / monitor.
- `python -m unittest discover -s tests -v`: 20 tests passed.
- Exhaustive priority combinations for Error / Water / Disk.
- Disabled rules fall through to the next status.
- Unknown data cannot select green Running; known disk alarm remains visible.
- Normal stop does not latch an error.
- Error survives Stop/disconnect; acknowledgment cannot clear an active source.
- Optional every-stop error does not infer Stop from a disconnect sample.
- Disk GB OR percent boundaries and recovery.
- Settings round trip and validation, including non-finite values.
- Nested namespace traversal with fake COM objects.
- COM worker attaches to an existing fake object and does not call Open/Start/Quit.
- Simulated BLE verifies the primary RGB 98% workaround.
- Simulated BLE verifies Blink → Solid and Blink → OFF cancel the old pattern.

## Pending on Windows lab PC

- GUI visual/interaction check; no graphical display server was available here.
- Live CANoe COM behavior, including sysvar availability after Stop and reconnect.
- Compile the CAPL example in the installed CANoe version.
- Actual BLE scan/connect/reconnect, physical colors, brightness and blink timing.
- Windows executable build and launch.

This package includes source and a Windows build script, not a prebuilt EXE.

## Added in 1.0.1

Six mocked tests cover direct attach, existing ROT fallback, actionable missing-object errors, ambiguity rejection, ROT filtering and HRESULT formatting. Total: 20 passing tests. No live Windows/CANoe validation is claimed. Diagnostic reports are generated locally by the user and are not included in the source package.

## Added in 1.0.2

Installer/launcher review: validate the executable rather than checking file existence only; select an installed 64-bit Python with Tk; rename a broken environment before replacing it; check dependency imports after installation. Python compile and all 20 existing tests pass. Windows batch execution is pending; the automated tests do not cover cmd.exe or the installer. No change to CANoe attachment logic in this version.

## Prepared 1.0.3 Windows portable build

Added a PyInstaller onedir specification, asInvoker manifest, and Windows GitHub Actions build workflow. Added --simulate-led --smoke-test-report for a CI-only packaged GUI check. Python compile and existing 20 tests pass locally. No Windows EXE has yet been built. See ci/BUILD_PLAN_TH.md for exact proposed repository/branch changes before upload approval.
