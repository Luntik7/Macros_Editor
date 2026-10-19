import unittest
from queue import Empty
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock, patch

from pynput.keyboard import Key

from macros_hotkeys import MacroHotkeys
from macros_runner import play_macro, resolve_key


class HotkeyTests(unittest.TestCase):
    def setUp(self):
        patcher = patch("macros_hotkeys.Listener")
        self.listener = patcher.start().return_value
        self.addCleanup(patcher.stop)

    def manager(self, macros):
        return MacroHotkeys(macros, resolve_key, Mock())

    def event(self, manager, vk, scan, down=True, flags=0):
        return manager._filter(
            0x0100 if down else 0x0101,
            SimpleNamespace(vkCode=vk, scanCode=scan, flags=flags),
        )

    def test_modifier_macro_runs_after_release_with_its_original_delay(self):
        actions = [
            ("down", "ALT"), ("down", "SHIFT"), ("delay", 0.1),
            ("up", "ALT"), ("up", "SHIFT"),
        ]
        manager = self.manager({"alt + shift": actions})
        for vk, scan, down in [(0xA4, 56, True), (0xA0, 42, True),
                               (0xA4, 56, False)]:
            self.event(manager, vk, scan, down)
        with self.assertRaises(Empty):
            manager.jobs.get_nowait()
        cancel = manager.cancel
        self.event(manager, 0xA0, 42, down=False)
        queued_actions, queued_cancel = manager.jobs.get_nowait()
        self.assertEqual(queued_actions, actions)
        self.assertIs(queued_cancel, cancel)
        manager.jobs.put((queued_actions, queued_cancel))
        manager.jobs.put(None)
        manager.play_macro = Mock(wraps=play_macro)
        controller = Mock()
        with patch("macros_runner.Controller", return_value=controller), patch.object(cancel, "wait", return_value=False) as wait:
            manager._work()
        manager.play_macro.assert_called_once_with(actions, stop_event=cancel)
        wait.assert_called_once_with(0.1)
        self.assertEqual(controller.press.call_count, 2)
        self.assertEqual(controller.release.call_count, 2)
        self.assertFalse(manager.pressed)
        self.assertFalse(manager.busy)
        self.listener.suppress_event.assert_not_called()

    def test_digit_and_numpad_do_not_match_arrow(self):
        for vk, scan, flags in [(0x34, 5, 0), (0x64, 75, 0)]:
            manager = self.manager({"4": [("down", "F")]})
            self.event(manager, vk, scan, flags=flags)
            self.assertTrue(manager.busy)
        manager = self.manager({"4": []})
        self.event(manager, 0x25, 75, flags=1)
        self.assertFalse(manager.busy)

    def test_generic_shift_accepts_both_sides(self):
        for vk, scan in [(0xA0, 42), (0xA1, 54)]:
            with self.subTest(vk=vk):
                manager = self.manager({"ctrl + shift + esc": []})
                self.assertEqual(manager.bindings[0][0][1], {0x10, 0xA0, 0xA1})
                self.event(manager, 0xA2, 29)
                self.event(manager, vk, scan)
                self.event(manager, 0x1B, 1)
                self.assertTrue(manager.busy)

    def test_explicit_shift_keeps_its_side(self):
        manager = self.manager({"left shift + f": [], "right shift + f": []})
        self.assertEqual(manager.bindings[0][0][0], {0xA0})
        self.assertEqual(manager.bindings[1][0][0], {0xA1})

    def test_waits_for_every_trigger_key_and_ignores_fake_shift(self):
        actions = [("down", "F"), ("up", "F")]
        manager = self.manager({"ctrl + shift + esc": actions})
        for vk, scan in [(0xA2, 29), (0xA0, 42), (0x1B, 1)]:
            self.event(manager, vk, scan)
        self.listener.suppress_event.assert_called_once()
        self.event(manager, 0xA0, 554, down=False)
        self.assertIn((42, False), manager.pressed)
        self.event(manager, 0x1B, 1, down=False)
        self.event(manager, 0xA0, 42, down=False)
        with self.assertRaises(Empty):
            manager.jobs.get_nowait()
        self.event(manager, 0xA2, 29, down=False)
        job, cancel = manager.jobs.get_nowait()
        self.assertEqual(job, actions)
        self.assertFalse(cancel.is_set())
        self.assertFalse(manager.pressed)

    def test_injected_events_cannot_start_macro(self):
        manager = self.manager({"1": [("down", "1"), ("up", "1")]})
        self.event(manager, 0x31, 2, flags=0x10)
        self.event(manager, 0x31, 2, down=False, flags=0x90)
        self.assertFalse(manager.busy)
        self.assertFalse(manager.pressed)
        self.listener.suppress_event.assert_not_called()

    def test_repeat_does_not_queue_more_macros_and_pause_cancels(self):
        manager = self.manager({"4": []})
        self.event(manager, 0x34, 5)
        token = manager.cancel
        self.event(manager, 0x34, 5)
        manager.pause()
        self.assertTrue(token.is_set())
        self.event(manager, 0x34, 5, down=False)
        with self.assertRaises(Empty):
            manager.jobs.get_nowait()
        self.assertFalse(manager.busy)

    def test_worker_skips_cancelled_jobs(self):
        manager = self.manager({})
        cancel = Event()
        cancel.set()
        manager.jobs.put(([], cancel))
        manager.jobs.put(None)
        manager._work()
        manager.play_macro.assert_not_called()

    def test_playback_cancellation_releases_held_keys(self):
        cancel = Event()
        controller = Mock()
        controller.press.side_effect = lambda key: cancel.set()
        with patch("macros_runner.Controller", return_value=controller):
            play_macro([("down", "SHIFT"), ("delay", 10), ("up", "SHIFT")], cancel)
        controller.release.assert_called_once_with(Key.shift)

    def test_playback_error_releases_held_keys(self):
        controller = Mock()
        with patch("macros_runner.Controller", return_value=controller):
            with self.assertRaises(ValueError):
                play_macro([("down", "CTRL"), ("down", "invalid key")])
        controller.release.assert_called_once_with(Key.ctrl)


if __name__ == "__main__":
    unittest.main()
