import keyboard
import pystray
import time
from PIL import Image, ImageDraw
from macros_storage import load_macros, load_settings
from macros_instance import acquire_runner_lock, release_runner_lock
from threading import Lock
from threading import Thread


settings = load_settings()
play_lock = Lock()


def play_macro(actions):
    print("Вхід у play_macro", flush=True)
    if not play_lock.acquire(blocking=False):
        print("Lock busy", flush=True)
        return
    print("Lock received", flush=True)
    try:
        for action, key in actions:
            if action == "delay":
                time.sleep(float(key))
                continue

            key = key.lower()

            if key == "left windows":
                key = "windows"

            if action == "down":
                keyboard.press(key)

            elif action == "up":
                keyboard.release(key)

    finally:
        play_lock.release()


def register_macros():
    for trigger, actions in load_macros().items():
        keyboard.add_hotkey(
            trigger,
            lambda actions=actions: Thread(
                target=play_macro,
                args=(actions,),
                daemon=False,
            ).start(),
            suppress=True,
        )


def create_icon(color="green"):
    image = Image.new("RGB", (64, 64), "black")
    draw = ImageDraw.Draw(image)
    draw.rectangle((16, 16, 48, 48), fill=color)
    return image


def close_program(icon, item):
    keyboard.clear_all_hotkeys()
    icon.stop()

    


def start():
    runner_lock = acquire_runner_lock()
    if runner_lock is None:
        return

    paused = False

    def toggle_pause(icon, item):
        nonlocal paused

        if paused:
            register_macros()
        else:
            keyboard.clear_all_hotkeys()

        paused = not paused
        icon.icon = create_icon("red" if paused else "green")
        icon.update_menu()

    try:
        register_macros()

        tray = pystray.Icon(
            name="macros_editor",
            icon=create_icon(),
            title="Macros Editor",
            menu=pystray.Menu(
                pystray.MenuItem(
                    lambda item: "Resume" if paused else "Pause",
                    toggle_pause,
                ),
                pystray.MenuItem("Exit", close_program),
            ),
        )

        tray.run()
    finally:
        try:
            keyboard.clear_all_hotkeys()
        finally:
            release_runner_lock(runner_lock)


if __name__ == "__main__":
    start()
