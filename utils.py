import os


def clear_console():
    os.system("cls")


def message_with_pause(msg):
    pause = input(msg)