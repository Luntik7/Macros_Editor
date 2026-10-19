import questionary

from macros_storage import load_macros
from utils import clear_console, message_with_pause


def show_macro(trigger, actions):
    clear_console()
    title = f"=== {trigger} ==="
    print(f"{title:^35}\n")
    

    if not actions:
        print("This macro has no actions.")

    for index, (action, value) in enumerate(actions, start=1):
        if action == "delay":
            description = f"{"◷":<3} {value}s"
        elif action == "down":
            description = f"{"↓":<3} {value}"
        elif action == "up":
            description = f"{"↑":<3} {value}"
        else:
            description = f"{action}: {value}"

        print(f"{index:>3}. {description}")

    message_with_pause("\nPress Enter to return to the list...")


def view_macros():
    macros = load_macros()
    back = object()

    if not macros:
        clear_console()
        message_with_pause("No macros. Press Enter to exit...")
        return

    while True:
        clear_console()
        choices = [
            questionary.Choice(
                title=f"{trigger:<25} ({len(actions)} actions)",
                value=trigger,
            )
            for trigger, actions in macros.items()
        ]
        choices.append(questionary.Choice("BACK", value=back))

        trigger = questionary.select(
            "\n=== Macros ===",
            choices=choices,
            qmark="",
        ).ask()

        if trigger is None or trigger is back:
            return

        show_macro(trigger, macros[trigger])
