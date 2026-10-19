# Known issue: Windows keyboard handling

Status: fixes under testing; live verification pending (2026-10-19). The symptoms below describe the earlier `keyboard`-based runner.

- Incorrect playback: a macro assigned to `4` / NumPad 4 and intended to send Ctrl+F can open Calculator. The captured events show injected `LAUNCH APP2` (`vk=0xB7`) instead of F (`vk=0x46`). This confirms incorrect key translation during playback.
- Trigger collisions: `4`, NumPad 4, and the left arrow can activate the same macro because the current name-to-scan-code mapping does not distinguish them reliably.
- Intermittent modifier issues: Alt+Shift may fail to switch the input language, and Shift can appear stuck. Near lines 805–823 of `logs/keyboard_20261019_191229_650178.log`, Shift events use the Windows simulated scan code `554` (`0x22A`), rather than the usual `42`. The exact cause of the stuck state is not yet confirmed; suppression and modifier-state tracking need further investigation.

The experimental `macros_keyboard.py` workarounds were removed. After changing playback alone, `logs/keyboard_20261019_201001_010141.log` showed correct F events but continued Alt/Shift problems while `keyboard` still handled triggers.

The runner now uses `pynput` for both playback and trigger handling. It ignores injected events for trigger matching, excludes simulated Shift events from physical-key tracking, forwards physical modifiers, and waits for trigger release before playback. All registered macros run their original actions and delays, including modifier shortcuts mapped to themselves. Since physical modifiers pass through, such a shortcut can perform its native action and then repeat it through the macro. Pause and Exit cancel playback and release keys held by the macro. Ten automated tests cover these cases with simulated input; real keyboard behavior still needs verification. The recorder continues to use `keyboard`.

To capture a reproduction, start the tray, then run `python keyboard_logger.py`, reproduce the issue, and release F12 to stop logging. Logs are saved under `logs/keyboard_*.log`; they contain keyboard activity from the session, so review them before sharing.

Planned direction: use a shared, explicit Windows key mapping for recording, trigger matching, and playback while retaining the readable macro JSON format.
