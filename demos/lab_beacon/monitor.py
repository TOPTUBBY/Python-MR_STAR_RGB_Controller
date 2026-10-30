"""COM lives in a disposable subprocess so RPC stalls cannot block Tk/BLE."""
import time
from core import read_sysvar
from canoe_attach import connect_once


def canoe_worker(out, stop, config):
    try:
        import pythoncom
        from win32com.client import dynamic
    except ImportError:
        out.put({'connected': False, 'running': None, 'detail': 'CANoe requires Windows + pywin32', 'time': time.monotonic()})
        return
    pythoncom.CoInitialize()
    app = None
    method = ''
    activation_pending = bool(config.get('_activate_once', False))
    try:
        while not stop.is_set():
            result = {'connected': False, 'running': None, 'error': None, 'water': None, 'warnings': [], 'time': time.monotonic()}
            try:
                if app is None:
                    # Consume before calling, so failure/close/reconnect cannot
                    # activate CANoe a second time without another button click.
                    activate = activation_pending
                    activation_pending = False
                    app, method = connect_once(pythoncom, dynamic, activate=activate)
                result['running'] = bool(app.Measurement.Running)
                result['connected'] = True
                result['detail'] = ('Running' if result['running'] else 'Stopped') + ' | ' + method
                for key in ('error', 'water'):
                    if config[key + '_enabled']:
                        try:
                            result[key] = read_sysvar(app, config[key + '_variable']) == config[key + '_value']
                        except Exception as exc:
                            result['warnings'].append(key + ' sysvar unavailable: ' + str(exc))
                    else:
                        result[key] = False
            except Exception as exc:
                app = None
                result['detail'] = 'CANoe connection unavailable: ' + str(exc)
            result['time'] = time.monotonic()
            out.put(result)
            pythoncom.PumpWaitingMessages()
            stop.wait(0.25)
    finally:
        app = None
        pythoncom.CoUninitialize()
