import contextlib
import os
import subprocess
import sys
import threading
import time

import psutil
import pythoncom
import win32con
import win32console
import win32gui
import winreg
from win32com.client import Dispatch

from .logger import log
from . import state


def WaitAndExit():
    if Is_run_by_exe():
        win32gui.ShowWindow(state.window, win32con.SW_SHOW)

    from .presence import Presence

    Presence.stop()
    input("Press Enter to close the program.")

    if Is_run_by_exe():
        win32gui.PostMessage(state.window, win32con.WM_CLOSE, 0, 0)
    else:
        sys.exit(0)


def toggle_auto_start_windows():
    state.auto_start_windows = not state.auto_start_windows
    log(f"Bool auto_start_windows set state: {state.auto_start_windows}")

    def create_shortcut(target, shortcut_path, description="", arguments=""):
        pythoncom.CoInitialize()
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = target
        shortcut.WorkingDirectory = os.path.dirname(target)
        shortcut.Description = description
        shortcut.Arguments = arguments
        shortcut.Save()

    def change_setting(tglle: bool):
        if tglle:
            try:
                exe_path = os.path.abspath(sys.argv[0])
                shortcut_path = os.path.join(
                    os.getenv("APPDATA"),
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "Startup",
                    "YandexMusicRPC.lnk",
                )
                create_shortcut(exe_path, shortcut_path, arguments="--run-through-startup")
            except Exception:
                exe_path = f'"{os.path.abspath(sys.argv[0])}" --run-through-startup'
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                    0,
                    winreg.KEY_SET_VALUE,
                )
                winreg.SetValueEx(key, "YandexMusicRPC", 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)
        else:
            shortcut_path = os.path.join(
                os.getenv("APPDATA"),
                "Microsoft",
                "Windows",
                "Start Menu",
                "Programs",
                "Startup",
                "YandexMusicRPC.lnk",
            )
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)

            with contextlib.suppress(FileNotFoundError):
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                    0,
                    winreg.KEY_ALL_ACCESS,
                )
                winreg.DeleteValue(key, "YandexMusicRPC")
                winreg.CloseKey(key)

    threading.Thread(target=change_setting, args=[state.auto_start_windows]).start()


def is_in_autostart() -> bool:
    def is_in_startup():
        shortcut_path = os.path.join(
            os.getenv("APPDATA"),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
            "Startup",
            "YandexMusicRPC.lnk",
        )
        return os.path.exists(shortcut_path)

    def is_in_registry():
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ,
            )
            winreg.QueryValueEx(key, "YandexMusicRPC")
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False

    return is_in_startup() or is_in_registry()


def toggle_console():
    if state.window and win32gui.IsWindowVisible(state.window):
        win32gui.ShowWindow(state.window, win32con.SW_HIDE)
    else:
        Show_Console_Permanent()


def Is_already_running() -> bool:
    return bool(win32gui.FindWindow(None, "YandexMusicRPC - Console"))


def Is_windows_11() -> bool:
    return sys.getwindowsversion().build >= 22000


def Check_conhost():
    if Is_windows_11() and "--run-through-conhost" not in sys.argv:
        _extracted_from_Check_conhost_3()

    if ("--run-through-launcher" in sys.argv or "--run-through-conhost" in sys.argv) and len(sys.argv) > 2:
        first_pid = int(sys.argv[2])
        try:
            parent_process = psutil.Process(first_pid)
            for child in parent_process.children(recursive=True):
                child.terminate()
            parent_process.terminate()
            parent_process.wait(timeout=3)
        except Exception:
            print(f"Couldn't close the process: {first_pid}")


def _extracted_from_Check_conhost_3():
    Run_by_startup_without_conhost()
    print("Wait a few seconds for the script to load...")
    script_path = os.path.abspath(sys.argv[0])
    first_pid = os.getpid()
    subprocess.Popen(
        ["start", "/min", "conhost.exe", script_path, "--run-through-conhost", str(first_pid)] + sys.argv[1:],
        shell=True,
    )
    event = threading.Event()
    event.wait()


def Show_Console_Permanent():
    if state.window:
        win32gui.ShowWindow(state.window, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(state.window)


def Check_run_by_startup():
    if state.window:
        if "--run-through-startup" not in sys.argv:
            Show_Console_Permanent()
            log("Minimize to system tray in 3 seconds...")
            time.sleep(3)
        win32gui.ShowWindow(state.window, win32con.SW_HIDE)
    else:
        from .enums import LogType
        log("Console window not found", LogType.Error)


def Run_by_startup_without_conhost():
    if console_window := win32console.GetConsoleWindow():
        if "--run-through-startup" in sys.argv:
            win32gui.ShowWindow(console_window, win32con.SW_HIDE)
    else:
        from .enums import LogType
        log("Console window not found", LogType.Error)


def Disable_close_button():
    if hwnd := win32console.GetConsoleWindow():
        if hMenu := win32gui.GetSystemMenu(hwnd, False):
            win32gui.DeleteMenu(hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND)


def Set_ConsoleMode():
    hStdin = win32console.GetStdHandle(win32console.STD_INPUT_HANDLE)
    mode = hStdin.GetConsoleMode()
    new_mode = mode & ~0x0040
    hStdin.SetConsoleMode(new_mode)


def Is_run_by_exe() -> bool:
    script_path = os.path.abspath(sys.argv[0])
    return bool(script_path.endswith(".exe"))


def Get_IconPath():
    try:
        if getattr(sys, "frozen", False):
            resources_path = sys._MEIPASS
        else:
            resources_path = os.path.dirname(os.path.abspath(sys.argv[0]))

        return f"{resources_path}/assets/YMRPC_ico.ico"
    except Exception:
        return None
