from utils import clear_console
import keyboard
from queue import Queue
import dotenv


def record_trigger():
    clear_console()

    print("=== TRIGGER RECORDING ===")

    events = Queue()
    hook = keyboard.hook(events.put, suppress=True)

    pressed_keys = []
    active_keys = set()
    cancel_requested = False

    try:
        while True:
            event = events.get()
            key = event.name.lower()

            if not pressed_keys and key == "enter":
                if event.event_type == keyboard.KEY_DOWN:
                    cancel_requested = True
                elif event.event_type == keyboard.KEY_UP and cancel_requested:
                    return None

                continue

            if event.event_type == keyboard.KEY_DOWN:
                if key not in active_keys and key not in pressed_keys:
                    active_keys.add(key)
                    pressed_keys.append(str(key))
                    print(f"\r{' + '.join(pressed_keys)}", end='', flush=True)

            elif event.event_type == keyboard.KEY_UP:
                active_keys.discard(key)

                if pressed_keys and not active_keys:
                    return pressed_keys

    finally:
        keyboard.unhook(hook)
    

def record_macro(stop_button = 'f8', record_user_input_delay=False, min_delay=0.03):
    print("=== MACROS RECORDING ===")
    print(f"(Press {stop_button.upper()} to finish)\n")

    events = Queue()
    hook = keyboard.hook(events.put, suppress=True)

    actions = []
    active_keys = set()
    last_event_time = None

    try:
        while True:
            event = events.get()
            key = event.name.lower()

            if key == stop_button.lower() and event.event_type == keyboard.KEY_DOWN:
                for pressed_key in active_keys:     #to avoid permanently pressed buttons after macro play
                    actions.append(("up", pressed_key.upper()))
                return actions

            action = None
            if event.event_type == keyboard.KEY_DOWN:
                if key not in active_keys:
                    action = "down"
                    active_keys.add(key)

            elif event.event_type == keyboard.KEY_UP:
                if key in active_keys:
                    action = "up"
                    active_keys.discard(key)

            if action is not None:
                if record_user_input_delay and last_event_time is not None:
                    delay = event.time - last_event_time
                    if delay > 0 and delay >= min_delay:
                        rounded_delay = round(delay, 2)
                        actions.append(("delay", rounded_delay))
                        print(rounded_delay, "s-delay")

                actions.append((action, key.upper()))
                last_event_time = event.time
                print("↓ " if action == "down" else "↑ ", key.upper())

    finally:
        keyboard.unhook(hook)


def create_macro(stop_button:str, record_user_input_delay:bool, min_delay:float):
    trigger_keys = record_trigger()

    if trigger_keys is None:
        return None

    trigger = " + ".join(trigger_keys)
    print('\n')
    actions = record_macro(stop_button=stop_button, record_user_input_delay=record_user_input_delay, min_delay=min_delay)

    if not actions:
        return None

    return {
        "trigger": trigger,
        "actions": actions,
    }
