import multiprocessing
import os
import sys
import threading

import win32console

from ymrpc.constants import REPO_URL
from ymrpc.enums import LogType
from ymrpc.logger import log
from ymrpc.presence import Presence
from ymrpc.settings import get_saves_settings
from ymrpc.token_manager import Init_yaToken
from ymrpc.tray import create_tray_icon, tray_thread
from ymrpc.version_check import GetLastVersion
from ymrpc.windows import (
    Check_conhost,
    Check_run_by_startup,
    Disable_close_button,
    Is_already_running,
    Is_run_by_exe,
    Set_ConsoleMode,
    Show_Console_Permanent,
    WaitAndExit,
)
from ymrpc import state


def main():
    multiprocessing.freeze_support()

    try:
        if Is_run_by_exe():
            Check_conhost()
            Set_ConsoleMode()

            log("Launched. Check the actual version...")
            GetLastVersion(REPO_URL)

            get_saves_settings(True)

            state.mainMenu = create_tray_icon()
            icon_thread = threading.Thread(target=tray_thread, args=(state.mainMenu,))
            icon_thread.daemon = True
            icon_thread.start()

            state.window = win32console.GetConsoleWindow()

            if Is_already_running():
                log("YandexMusicRPC is already running.", LogType.Error)
                Show_Console_Permanent()
                WaitAndExit()
                return

            win32console.SetConsoleTitle("YandexMusicRPC - Console")
            Disable_close_button()
            Check_run_by_startup()
        else:
            get_saves_settings(True)
            log("Launched without minimizing to tray and other and other gui functions")

        Init_yaToken(False)

        Presence.start()

    except KeyboardInterrupt:
        log("Keyboard interrupt received, stopping...")
        Presence.stop()


if __name__ == "__main__":
    main()
