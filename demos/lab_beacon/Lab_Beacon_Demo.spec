# Windows portable folder build; run on Windows with Python 3.13 x64.
from pathlib import Path
base = Path(SPECPATH)
a = Analysis(
    [str(base / 'app.py')],
    pathex=[str(base)],
    binaries=[],
    datas=[],
    hiddenimports=['pythoncom', 'pywintypes', 'win32com.client',
                   'bleak.backends.winrt', 'bleak.backends.winrt.client',
                   'bleak.backends.winrt.scanner'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name='Lab_Beacon_Demo', debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    manifest=str(base / 'ci' / 'as_invoker.manifest'),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False,
               name='Lab_Beacon_Demo')
