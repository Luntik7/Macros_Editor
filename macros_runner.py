import pystray
import time
from PIL import Image, ImageDraw
from pynput.keyboard import Controller, Key, KeyCode
from macros_storage import load_macros, load_settings
from macros_instance import acquire_runner_lock, release_runner_lock
from macros_hotkeys import MacroHotkeys
from threading import Lock


settings = load_settings()
play_lock = Lock()


def resolve_key(name):
    name = name.lower()
    if len(name) == 1:
        if name in "abcdefghijklmnopqrstuvwxyz0123456789":
            return KeyCode.from_vk(ord(name.upper()))
        return KeyCode.from_char(name)

    aliases = {
        "left ctrl": "ctrl_l", "right ctrl": "ctrl_r",
        "left alt": "alt_l", "right alt": "alt_r", "alt gr": "alt_gr",
        "left shift": "shift_l", "right shift": "shift_r",
        "windows": "cmd", "left windows": "cmd_l", "right windows": "cmd_r",
        "escape": "esc", "return": "enter", "menu": "menu",
        "volume up": "media_volume_up", "volume down": "media_volume_down",
        "volume mute": "media_volume_mute",
    }
    key = getattr(Key, aliases.get(name, name.replace(" ", "_")), None)
    if key is None:
        raise ValueError(f"Unsupported macro key: {name!r}")
    return key


def play_macro(actions, stop_event=None):
    if not play_lock.acquire(blocking=False):
        return

    pressed_keys = []

    try:
        controller = Controller()
        for action, key in actions:
            if stop_event is not None and stop_event.is_set():
                break
            if action == "delay":
                if stop_event is None:
                    time.sleep(float(key))
                elif stop_event.wait(float(key)):
                    break
                continue

            key = resolve_key(key)

            if action == "down":
                if key not in pressed_keys:
                    pressed_keys.append(key)
                controller.press(key)

            elif action == "up":
                controller.release(key)
                if key in pressed_keys:
                    pressed_keys.remove(key)
            else:
                raise ValueError(f"Unsupported macro action: {action!r}")

    finally:
        try:
            for key in reversed(pressed_keys):
                try:
                    controller.release(key)
                except Exception as error:
                    print(f"Could not release macro key {key!r}: {error}", flush=True)
        finally:
            play_lock.release()


def register_macros():
    return MacroHotkeys(
        load_macros(), resolve_key, play_macro,
        suppress=settings.get("suppress_hotkeys", True),
    )


def create_icon(color="green"):
    image = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill=color)
    return image


def close_program(icon, item, hotkeys):
    hotkeys.pause()
    icon.stop()

    


def start():
    runner_lock = acquire_runner_lock()
    if runner_lock is None:
        return

    paused = False
    hotkeys = None

    def toggle_pause(icon, item):
        nonlocal paused

        if paused:
            hotkeys.resume(load_macros())
        else:
            hotkeys.pause()

        paused = not paused
        icon.icon = create_icon("red" if paused else "green")
        icon.update_menu()

    try:
        hotkeys = register_macros()
        hotkeys.start()

        tray = pystray.Icon(
            name="macros_editor",
            icon=create_icon(),
            title="Macros Editor",
            menu=pystray.Menu(
                pystray.MenuItem(
                    lambda item: "Resume" if paused else "Pause",
                    toggle_pause,
                ),
                pystray.MenuItem("Exit", lambda icon, item: close_program(icon, item, hotkeys)),
            ),
        )

        tray.run()
    finally:
        try:
            if hotkeys is not None:
                hotkeys.stop()
        finally:
            release_runner_lock(runner_lock)


if __name__ == "__main__":
    start()
