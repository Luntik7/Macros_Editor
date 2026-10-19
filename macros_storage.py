import json
import re
from pathlib import Path


MACROS_FILE = Path("config/macros.json")
SETTINGS_FILE = Path("config/settings.json")


def save_macro(trigger: str, actions: list[tuple[str, str]]):
    macros = load_macros()
    macros[trigger] = actions

    text = json.dumps(
        macros,
        ensure_ascii=False,
        indent=4,
    )

    text = re.sub(
        r'\[\s*("(?:[^"\\]|\\.)*"),\s*("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*\]',
        r'[\1, \2]',
        text
    )

    with MACROS_FILE.open("w", encoding="utf-8") as file:
        file.write(text)


def read_json_file(file_path:Path):
    if not file_path.exists():
        return {}

    content = file_path.read_text(
        encoding="utf-8",
    ).strip()

    if not content:
        return {}

    return json.loads(content)


def load_macros() -> dict:
    data = read_json_file(MACROS_FILE)

    return {
        trigger: [tuple(action) for action in actions]
        for trigger, actions in data.items()
    }


def load_settings():
    data = read_json_file(SETTINGS_FILE)
    return data
