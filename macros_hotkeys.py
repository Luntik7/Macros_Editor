"""Windows macro triggers using pynput's raw event filter."""

from queue import SimpleQueue
from threading import Event, Lock, Thread

from pynput.keyboard import Listener


MODIFIERS = {
    0x10: {0x10, 0xA0, 0xA1},
    0x11: {0x11, 0xA2, 0xA3},
    0x12: {0x12, 0xA4, 0xA5},
    0x5B: {0x5B, 0x5C},
}
MODIFIER_VKS = set().union(*MODIFIERS.values())


class MacroHotkeys:
    def __init__(self, macros, resolve_key, play_macro, suppress=True):
        self.resolve_key = resolve_key
        self.play_macro = play_macro
        self.suppress = suppress
        self.bindings = self._compile(macros)
        self.pressed = {}
        self.suppressed = set()
        self.pending = None
        self.cancel = None
        self.busy = False
        self.paused = False
        self.lock = Lock()
        self.jobs = SimpleQueue()
        self.listener = Listener(win32_event_filter=self._filter)
        self.worker = Thread(target=self._work, name="macro-playback")


    def _vk(self, name):
        key = self.resolve_key(name)
        vk = getattr(getattr(key, "value", key), "vk", None)
        if vk is None:
            raise ValueError(f"Trigger key needs a Windows VK code: {name!r}")
        return vk


    def _compile(self, macros):
        bindings = []
        for trigger, actions in macros.items():
            names = [name.strip().lower() for name in trigger.split("+")]
            options = []
            for name in names:
                vk = self._vk(name)
                choices = {vk}
                if name in ("ctrl", "alt", "shift", "windows", "cmd"):
                    for modifier_codes in MODIFIERS.values():
                        if vk in modifier_codes:
                            choices = modifier_codes
                            break
                elif len(name) == 1 and name.isascii() and name.isdigit():
                    # Preserve digit triggers on the number row and NumPad,
                    # without confusing either with the navigation arrows.
                    choices = {vk, 0x60 + int(name)}
                options.append(choices)

            bindings.append((options, actions))
        return sorted(bindings, key=lambda binding: len(binding[0]), reverse=True)


    def _filter(self, message, data):
        # These events still reach Windows; False only skips pynput callbacks.
        if data.flags & 0x12 or data.scanCode in (0x22A, 0x236):
            return False
        if message not in (0x0100, 0x0101, 0x0104, 0x0105):
            return False

        identity = (data.scanCode, bool(data.flags & 1))
        down = message in (0x0100, 0x0104)
        with self.lock:
            block = identity in self.suppressed
            repeated = identity in self.pressed
            if down:
                self.pressed[identity] = data.vkCode
            else:
                self.pressed.pop(identity, None)
                self.suppressed.discard(identity)

            if self.pending is not None:
                held, actions, cancel = self.pending
                if not held.intersection(self.pressed):
                    self.pending = None
                    self.jobs.put((actions, cancel))

            if down and not repeated and not self.paused and not self.busy:
                vks = set(self.pressed.values())
                for options, actions in self.bindings:
                    if len(self.pressed) == len(options) and all(vks & option for option in options):
                        self.busy = True
                        self.cancel = Event()
                        self.pending = (set(self.pressed), actions, self.cancel)
                        # Forward physical modifiers immediately. Suppress only
                        # the main key, including repeats and its release.
                        if self.suppress and data.vkCode not in MODIFIER_VKS:
                            self.suppressed.add(identity)
                            block = True
                        break

        if block:
            self.listener.suppress_event()
        return False


    def _work(self):
        while True:
            job = self.jobs.get()
            if job is None:
                return
            actions, cancel = job
            try:
                if not cancel.is_set():
                    self.play_macro(actions, stop_event=cancel)
            except Exception as error:
                print(f"Macro failed: {error}", flush=True)
            finally:
                with self.lock:
                    self.busy = False


    def start(self):
        self.worker.start()
        self.listener.start()
        self.listener.wait()


    def pause(self):
        with self.lock:
            self.paused = True
            if self.cancel is not None:
                self.cancel.set()
            if self.pending is not None:
                self.pending = None
                self.busy = False


    def resume(self, macros):
        bindings = self._compile(macros)
        with self.lock:
            self.bindings = bindings
            self.paused = False


    def stop(self):
        self.pause()
        self.listener.stop()
        if self.listener.ident is not None:
            self.listener.join()
        self.jobs.put(None)
        if self.worker.ident is not None:
            self.worker.join()
