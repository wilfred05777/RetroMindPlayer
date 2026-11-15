"""Windows shell integration. Never deletes or moves files."""
import ctypes
import os


def reveal_file(path):
    if os.name != 'nt':
        raise OSError('File Explorer is available on Windows only.')
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    ole = ctypes.WinDLL('ole32', use_last_error=True)
    ole.CoInitializeEx.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    ole.CoInitializeEx.restype = ctypes.c_long
    initialized = ole.CoInitializeEx(None, 2)
    if initialized < 0 and (initialized & 0xffffffff) != 0x80010106:
        raise OSError(f'Windows COM initialization failed (0x{initialized & 0xffffffff:08X}).')
    pidl = ctypes.c_void_p()
    shell.SHParseDisplayName.argtypes = [ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p),ctypes.c_ulong,ctypes.c_void_p]
    shell.SHParseDisplayName.restype = ctypes.c_long
    shell.SHOpenFolderAndSelectItems.argtypes = [ctypes.c_void_p,ctypes.c_uint,ctypes.c_void_p,ctypes.c_ulong]
    shell.SHOpenFolderAndSelectItems.restype = ctypes.c_long
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    try:
        result = shell.SHParseDisplayName(str(path), None, ctypes.byref(pidl), 0, None)
        if result < 0:
            raise OSError(f'Windows could not resolve the file (0x{result & 0xffffffff:08X}).')
        result = shell.SHOpenFolderAndSelectItems(pidl, 0, None, 0)
        if result < 0:
            raise OSError(f'File Explorer failed (0x{result & 0xffffffff:08X}).')
    finally:
        if pidl:
            ole.CoTaskMemFree(pidl)
        if initialized >= 0:
            ole.CoUninitialize()
