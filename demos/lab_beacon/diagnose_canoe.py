"""Read-only diagnostic. Does not start, stop or register CANoe."""
import csv
import io
import ctypes
import getpass
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from canoe_attach import attach_existing, matching_rot_entries, hresult_text
from process_info import query_process


def diagnose():
    data = {'python': sys.version, 'python_bits': platform.architecture()[0], 'user': getpass.getuser(), 'pid': os.getpid()}
    if sys.platform != 'win32':
        data['error'] = 'Run this diagnostic on the Windows lab PC.'
        return data
    data['beacon_elevated'] = bool(ctypes.windll.shell32.IsUserAnAdmin())
    data['beacon_process_details'] = query_process(os.getpid())
    try:
        process = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], capture_output=True,
                                 text=True, timeout=5, creationflags=subprocess.CREATE_NO_WINDOW)
        data['process_query_returncode'] = process.returncode
        data['canoe_processes'] = [row for row in csv.reader(io.StringIO(process.stdout))
                                   if row and row[0].lower().startswith('canoe')]
        data['canoe_process_details'] = [query_process(int(row[1])) for row in data['canoe_processes'] if len(row) > 1 and row[1].isdigit()]
        if process.returncode != 0:
            data['process_query_error'] = process.stderr.strip() or process.stdout.strip()
    except Exception as exc:
        data['process_query_error'] = str(exc)
    import winreg
    data['registration'] = []
    for view, label in ((winreg.KEY_WOW64_64KEY, '64-bit registry'), (winreg.KEY_WOW64_32KEY, '32-bit registry')):
        entry = {'view': label}
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'CANoe.Application\CLSID', 0, winreg.KEY_READ | view) as key:
                entry['clsid'] = winreg.QueryValueEx(key, '')[0]
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, 'CLSID\\' + entry['clsid'] + r'\LocalServer32', 0, winreg.KEY_READ | view) as key:
                entry['server'] = winreg.QueryValueEx(key, '')[0]
        except OSError as exc:
            entry['error'] = str(exc)
        data['registration'].append(entry)
    try:
        import pythoncom
        from win32com.client import dynamic
    except ImportError as exc:
        data['error'] = 'Missing pywin32: run INSTALL_WINDOWS.bat. ' + str(exc)
        return data
    pythoncom.CoInitialize()
    try:
        try:
            app, method = attach_existing(pythoncom, dynamic)
            data['attach'] = {'success': True, 'method': method, 'running': bool(app.Measurement.Running)}
            app = None
        except Exception as exc:
            data['attach'] = {'success': False, 'message': str(exc), 'code': hresult_text(exc.__cause__ or exc)}
        try:
            _, entries = matching_rot_entries(pythoncom)
            data['matching_canoe_rot_names'] = [name for name, _ in entries]
        except Exception as exc:
            data['rot_error'] = str(exc)
    finally:
        pythoncom.CoUninitialize()
    return data


if __name__ == '__main__':
    result = diagnose()
    text = json.dumps(result, indent=2, ensure_ascii=False)
    print(text)
    folder = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'LabBeaconDemo'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / 'canoe_diagnostic.json'
    path.write_text(text, encoding='utf-8')
    print('\nReport saved:', path)
