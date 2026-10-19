# Known issue: Windows keyboard handling

Status: unresolved in the current version (2026-10-19).

- Incorrect playback: a macro assigned to `4` / NumPad 4 and intended to send Ctrl+F can open Calculator. The captured events show injected `LAUNCH APP2` (`vk=0xB7`) instead of F (`vk=0x46`). This confirms incorrect key translation during playback.
- Trigger collisions: `4`, NumPad 4, and the left arrow can activate the same macro because the current name-to-scan-code mapping does not distinguish them reliably.
- Intermittent modifier issues: Alt+Shift may fail to switch the input language, and Shift can appear stuck. Near lines 805–823 of `logs/keyboard_20261019_191229_650178.log`, Shift events use the Windows simulated scan code `554` (`0x22A`), rather than the usual `42`. The exact cause of the stuck state is not yet confirmed; suppression and modifier-state tracking need further investigation.

The experimental `macros_keyboard.py` workarounds were removed. The runner currently uses the original `keyboard` hotkey registration and name-based playback.

To capture a reproduction, start the tray, then run `python keyboard_logger.py`, reproduce the issue, and release F12 to stop logging. Logs are saved under `logs/keyboard_*.log`; they contain keyboard activity from the session, so review them before sharing.

Planned direction: use a shared, explicit Windows key mapping for recording, trigger matching, and playback while retaining the readable macro JSON format.
