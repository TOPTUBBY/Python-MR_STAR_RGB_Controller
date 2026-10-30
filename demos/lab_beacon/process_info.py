"""Read-only Windows token/session/image queries, no elevation requested."""
def query_process(pid):
    import ctypes
    from ctypes import wintypes
    result = {'pid': int(pid), 'elevated': None, 'session_id': None, 'path': None}
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    advapi = ctypes.WinDLL('advapi32', use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.ProcessIdToSessionId.argtypes = [wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.ProcessIdToSessionId.restype = wintypes.BOOL
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.QueryFullProcessImageNameW.restype = wintypes.BOOL
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD, ctypes.POINTER(wintypes.HANDLE)]
    advapi.OpenProcessToken.restype = wintypes.BOOL
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.LPVOID, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.GetTokenInformation.restype = wintypes.BOOL
    session = wintypes.DWORD()
    if kernel.ProcessIdToSessionId(pid, ctypes.byref(session)):
        result['session_id'] = session.value
    process = kernel.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION
    if not process:
        result['process_query_error'] = str(ctypes.WinError(ctypes.get_last_error()))
        return result
    try:
        size = wintypes.DWORD(32768)
        buf = ctypes.create_unicode_buffer(size.value)
        if kernel.QueryFullProcessImageNameW(process, 0, buf, ctypes.byref(size)):
            result['path'] = buf.value
        token = wintypes.HANDLE()
        if not advapi.OpenProcessToken(process, 0x0008, ctypes.byref(token)):  # TOKEN_QUERY
            result['token_query_error'] = str(ctypes.WinError(ctypes.get_last_error()))
            return result
        try:
            elevated, needed = wintypes.DWORD(), wintypes.DWORD()
            if advapi.GetTokenInformation(token, 20, ctypes.byref(elevated), ctypes.sizeof(elevated), ctypes.byref(needed)):
                result['elevated'] = bool(elevated.value)
            else:
                result['token_query_error'] = str(ctypes.WinError(ctypes.get_last_error()))
        finally:
            kernel.CloseHandle(token)
    finally:
        kernel.CloseHandle(process)
    return result
