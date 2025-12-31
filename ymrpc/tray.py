import webbrowser

import pystray
from PIL import Image
from yandex_music import exceptions

from .constants import REPO_URL
from .enums import LogType
from .logger import log
from .presence import Presence
from .settings import create_rpc_settings_menu
from .windows import Get_IconPath, toggle_auto_start_windows, toggle_console
from . import state


def tray_click(icon, query):
    match str(query):
        case "GitHub":
            webbrowser.open(REPO_URL, new=2)
        case "Exit":
            Presence.stop()
            icon.stop()
            # Window close is done via message to the console window.
            import win32con
            import win32gui

            if state.window:
                win32gui.PostMessage(state.window, win32con.WM_CLOSE, 0, 0)


def get_account_name() -> str:
    try:
        user_info = Presence.client.me.account
        account_name = user_info.display_name
        return account_name or "None"
    except exceptions.UnauthorizedError:
        return "Invalid token."
    except exceptions.NetworkError:
        return "Network error."
    except Exception:
        return "None"


def update_account_name(icon, new_account_name: str):
    rpc_settings_menu = create_rpc_settings_menu()
    settings_menu = pystray.Menu(
        pystray.MenuItem(f"Logged in as - {new_account_name}", lambda: None, enabled=False),
        pystray.MenuItem("Login to account...", lambda: _login_from_tray()),
    )

    icon.menu = pystray.Menu(
        pystray.MenuItem("Hide/Show Console", toggle_console, default=True),
        pystray.MenuItem("Start with Windows", toggle_auto_start_windows, checked=lambda item: state.auto_start_windows),
        pystray.MenuItem("Yandex settings", settings_menu),
        pystray.MenuItem("RPC settings", rpc_settings_menu),
        pystray.MenuItem("GitHub", tray_click),
        pystray.MenuItem("Exit", tray_click),
    )


def _login_from_tray():
    # Deferred import to avoid import cycles.
    from .token_manager import Init_yaToken

    Init_yaToken(True)


def create_tray_icon():
    tray_image = Image.open(Get_IconPath())
    account_name = get_account_name()
    rpc_settings_menu = create_rpc_settings_menu()

    settings_menu = pystray.Menu(
        pystray.MenuItem(f"Logged in as - {account_name}", lambda: None, enabled=False),
        pystray.MenuItem("Login to account...", lambda: _login_from_tray()),
    )

    return pystray.Icon(
        "YandexMusicRPC",
        tray_image,
        "YandexMusicRPC",
        menu=pystray.Menu(
            pystray.MenuItem("Hide/Show Console", toggle_console, default=True),
            pystray.MenuItem("Start with Windows", toggle_auto_start_windows, checked=lambda item: state.auto_start_windows),
            pystray.MenuItem("Yandex settings", settings_menu),
            pystray.MenuItem("RPC settings", rpc_settings_menu),
            pystray.MenuItem("GitHub", tray_click),
            pystray.MenuItem("Exit", tray_click),
        ),
    )


def tray_thread(icon):
    icon.run()
