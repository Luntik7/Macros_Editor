from utils import clear_console, message_with_pause
from macros_create import create_macro
from macros_storage import save_macro,  load_settings
from macros_view import view_macros
from macros_instance import is_runner_running
import questionary
import subprocess
from pathlib import Path

def main():
    settings = load_settings()
    base_dir = Path(__file__).resolve().parent
    runner_process = None

    while True:
        clear_console()
        
        choice = questionary.select(
            "\n=== Macro Recorder ===",
            choices = [
                "CREATE Macro",
                "VIEW Macroses",
                "RUN Macros Editor",
                "Exit",
            ],
            qmark = ""
        ).ask()

        if choice == "CREATE Macro":
            while True:
                clear_console()
                macro = create_macro(settings.get("stop_button", "f8"), settings.get("record_user_input_delay"), settings.get("min_delay"))
                
                if macro is None:
                    break

                choice = questionary.select(
                    "\nSave this macro?",
                    choices = ["Yes", "Try Again", "No"],
                    qmark = ""
                ).ask()

                if choice == 'Yes': 
                    save_macro(**macro)
                    break
                elif choice == "No":
                    break


        elif choice == "VIEW Macroses":
            view_macros()

        elif choice == "RUN Macros Editor":
            clear_console()
            if is_runner_running() or (
                runner_process is not None and runner_process.poll() is None
            ):
                message_with_pause(
                    "Macros Editor is already running. Use the tray icon to control it.\n"
                    "Press Enter to return to the menu..."
                )
                continue

            try:
                runner_process = subprocess.Popen(
                    [
                        str(base_dir / "venv" / "Scripts" / "pythonw.exe"),
                        str(base_dir / "macros_runner.py"),
                    ],
                    cwd=base_dir,
                )
            except OSError as error:
                message_with_pause(
                    f"Could not start Macros Editor: {error}\n"
                    "Press Enter to return to the menu..."
                )
            else:
                message_with_pause(
                    "Starting Macros Editor in the background.\n"
                    "Use the tray icon to pause, resume, or exit.\n"
                    "Press Enter to return to the menu..."
                )

        elif choice == "Exit":
            clear_console()
            break

        else:
            input("Невідома команда. Спробуйте ще раз.")


if __name__ == "__main__":
    main()
