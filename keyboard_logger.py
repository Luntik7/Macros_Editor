"""Observe Windows keyboard events independently of the macro runner. F12 stops."""

import ctypes
from ctypes import wintypes
from datetime import datetime
from pathlib import Path
from queue import SimpleQueue
from threading import Thread


class KeyboardEvent(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


def format_event(timestamp, message, vk, scan, flags, windows_time):
    action = "UP" if message in (0x0101, 0x0105) else "DOWN"
    names = {
        0xA0: "LEFT SHIFT", 0xA1: "RIGHT SHIFT",
        0xA2: "LEFT CTRL", 0xA3: "RIGHT CTRL",
        0xA4: "LEFT ALT", 0xA5: "RIGHT ALT",
        0x1B: "ESC", 0x7B: "F12", 0xB7: "LAUNCH APP2",
    }
    name = names.get(vk, chr(vk) if 0x30 <= vk <= 0x5A else f"VK_{vk:02X}")
    return (
        f"{timestamp.isoformat(timespec='milliseconds')} {action:<4} {name:<12} "
        f"vk=0x{vk:02X} scan={scan} flags=0x{flags:02X} "
        f"injected={bool(flags & 0x10)} extended={bool(flags & 0x01)} "
        f"windows_time={windows_time}"
    )


def main():
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    callback_type = ctypes.WINFUNCTYPE(
        ctypes.c_ssize_t, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
    )
    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, callback_type, wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = wintypes.HANDLE
    user32.CallNextHookEx.argtypes = [wintypes.HANDLE, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = ctypes.c_ssize_t
    user32.UnhookWindowsHookEx.argtypes = [wintypes.HANDLE]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL
    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = wintypes.BOOL
    user32.PostQuitMessage.argtypes = [ctypes.c_int]
    user32.PostQuitMessage.restype = None
    kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel32.GetModuleHandleW.restype = wintypes.HMODULE

    log_dir = Path(__file__).resolve().parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"keyboard_{datetime.now():%Y%m%d_%H%M%S_%f}.log"
    events = SimpleQueue()

    def write_events(file):
        while True:
            event = events.get()
            if event is None:
                return
            file.write(format_event(*event) + "\n")
            file.flush()

    @callback_type
    def on_key(code, message, data):
        if code >= 0 and message in (0x0100, 0x0101, 0x0104, 0x0105):
            event = ctypes.cast(data, ctypes.POINTER(KeyboardEvent)).contents
            events.put((datetime.now(), message, event.vkCode, event.scanCode, event.flags, event.time))
            if event.vkCode == 0x7B and message in (0x0101, 0x0105):
                user32.PostQuitMessage(0)
        return user32.CallNextHookEx(None, code, message, data)

    with log_path.open("w", encoding="utf-8") as file:
        file.write(f"Session started: {datetime.now().isoformat()}\n")
        file.flush()
        writer = Thread(target=write_events, args=(file,), name="keyboard-log-writer")
        writer.start()
        hook = None
        try:
            hook = user32.SetWindowsHookExW(13, on_key, kernel32.GetModuleHandleW(None), 0)
            if not hook:
                raise ctypes.WinError(ctypes.get_last_error())
            print(f"Logging keyboard events to: {log_path}", flush=True)
            print("Release F12 to stop. No keys are blocked or generated.", flush=True)
            message = wintypes.MSG()
            while True:
                result = user32.GetMessageW(ctypes.byref(message), None, 0, 0)
                if result == -1:
                    raise ctypes.WinError(ctypes.get_last_error())
                if result == 0:
                    break
        except KeyboardInterrupt:
            pass
        finally:
            if hook:
                user32.UnhookWindowsHookEx(hook)
            events.put(None)
            writer.join()
            file.write(f"Session ended: {datetime.now().isoformat()}\n")
    print("Logging stopped.")


if __name__ == "__main__":
    main()
