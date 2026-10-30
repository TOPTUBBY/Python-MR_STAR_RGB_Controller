"""Attach-only CANoe discovery. Never activate a COM server."""
import re


def hresult_text(exc):
    value = getattr(exc, 'hresult', None)
    if value is None and getattr(exc, 'args', ()) and isinstance(exc.args[0], int):
        value = exc.args[0]
    return f'0x{value & 0xffffffff:08X}' if isinstance(value, int) else type(exc).__name__


def registered_clsids():
    """Read both registry views, without modifying registration."""
    try:
        import winreg
    except ImportError:
        return set()
    values = set()
    for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r'CANoe.Application\CLSID', 0, winreg.KEY_READ | view) as key:
                values.add(winreg.QueryValueEx(key, '')[0].lower())
        except OSError:
            pass
    return values


def matching_rot_entries(pythoncom, clsids=None):
    """Enumerate existing CANoe monikers only; do not bind file monikers."""
    clsids = registered_clsids() if clsids is None else clsids
    rot = pythoncom.GetRunningObjectTable()
    context = pythoncom.CreateBindCtx(0)
    matches = []
    for moniker in rot.EnumRunning():
        try:
            name = moniker.GetDisplayName(context, None)
            lower = name.lower()
            # Never fetch an arbitrary file moniker or another application's object.
            named = re.search(r'(?<![a-z])canoe(?:\.application|[.:! _-]|$)', lower)
            if named or any(clsid in lower for clsid in clsids):
                matches.append((name, moniker))
        except Exception:
            continue
    return rot, matches


def attach_existing(pythoncom, dynamic):
    try:
        obj = pythoncom.GetActiveObject('CANoe.Application')
        return dynamic.Dispatch(obj), 'GetActiveObject'
    except Exception as direct_error:
        # Some registrations expose an instance moniker instead of the usual
        # active class entry. Fetching from ROT never launches CANoe.
        try:
            rot, entries = matching_rot_entries(pythoncom)
            usable = []
            for name, moniker in entries:
                try:
                    obj = rot.GetObject(moniker).QueryInterface(pythoncom.IID_IDispatch)
                    app = dynamic.Dispatch(obj)
                    bool(app.Measurement.Running)
                    usable.append((app, name))
                except Exception:
                    continue
            if len(usable) == 1:
                return usable[0][0], 'Running Object Table'
            if len(usable) > 1:
                raise RuntimeError('Multiple CANoe objects found. Keep one CANoe instance open and retry.')
        except RuntimeError:
            raise
        except Exception:
            pass
        code = hresult_text(direct_error)
        raise RuntimeError(
            f'{code}: no accessible active CANoe object. Check CANoe is open, '
            'same Windows user/elevation, and COM registration. Use Debug > Save CANoe diagnostic report.'
        ) from direct_error


def connect_once(pythoncom, dynamic, activate=False):
    """Normal attach first; activation is a single explicit user request only."""
    try:
        return attach_existing(pythoncom, dynamic)
    except RuntimeError as exc:
        if not activate or 'Multiple CANoe' in str(exc):
            raise
        try:
            obj = pythoncom.CoCreateInstance(
                pythoncom.CLSIDFromProgID('CANoe.Application'), None,
                pythoncom.CLSCTX_LOCAL_SERVER, pythoncom.IID_IDispatch)
            return dynamic.Dispatch(obj), 'Manual COM activation'
        except Exception as activation_error:
            raise RuntimeError('Manual COM activation failed: ' + hresult_text(activation_error)
                               + ': ' + str(activation_error)) from activation_error
