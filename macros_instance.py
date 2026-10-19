import ctypes
from ctypes import wintypes


MUTEX_NAME = r"Local\MyMacrosApp.Runner"
ERROR_ALREADY_EXISTS = 183

kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL


def acquire_runner_lock():
    handle = kernel32.CreateMutexW(None, False, MUTEX_NAME)
    error = ctypes.get_last_error()
    if not handle:
        raise ctypes.WinError(error)
    if error == ERROR_ALREADY_EXISTS:
        release_runner_lock(handle)
        return None
    return handle


def release_runner_lock(handle):
    kernel32.CloseHandle(handle)


def is_runner_running():
    handle = acquire_runner_lock()
    if handle is None:
        return True
    release_runner_lock(handle)
    return False
