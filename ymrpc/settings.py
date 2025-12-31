import pystray

from .enums import ButtonConfig, LanguageConfig, LogType
from .logger import log
from . import state
from .windows import is_in_autostart
from .presence import Presence


def get_saves_settings(fromStart: bool = False):
    state.auto_start_windows = is_in_autostart()

    state.button_config = state.config_manager.get_enum_setting(
        "UserSettings", "buttons_settings", ButtonConfig, fallback=ButtonConfig.BOTH
    )
    state.language_config = state.config_manager.get_enum_setting(
        "UserSettings", "language", LanguageConfig, fallback=LanguageConfig.RUSSIAN
    )

    if fromStart:
        log(
            f"Loaded settings: button_config = {state.button_config.name}, "
            f"language_config = {state.language_config.name}",
            LogType.Update_Status,
        )


def create_enum_menu(enum_class, get_setting_func, set_setting_func):
    def create_item(value):
        return pystray.MenuItem(
            value.name,
            lambda item: set_setting_func(value),
            checked=lambda item: get_setting_func("UserSettings", enum_class) == value,
        )

    return pystray.Menu(*[create_item(value) for value in enum_class])


def convert_to_enum(enum_class, value):
    if isinstance(value, enum_class):
        return value
    value_str = str(value)
    try:
        return enum_class[value_str]
    except KeyError:
        log(f"Invalid type: {value_str}")
        return None


def set_button_config(value):
    value = convert_to_enum(ButtonConfig, value)
    state.config_manager.set_enum_setting("UserSettings", "buttons_settings", value)
    log(f"Setting has been changed : buttons_settings to {value.name}")
    get_saves_settings()
    Presence.need_restart()


def set_language_config(value):
    value = convert_to_enum(LanguageConfig, value)
    state.config_manager.set_enum_setting("UserSettings", "language", value)
    log(f"Setting has been changed : language to {value.name}")
    get_saves_settings()
    Presence.need_restart()


def create_rpc_settings_menu():
    button_config_menu = create_enum_menu(
        ButtonConfig,
        lambda section, enum_type: state.config_manager.get_enum_setting(section, "buttons_settings", enum_type),
        set_button_config,
    )
    language_config_menu = create_enum_menu(
        LanguageConfig,
        lambda section, enum_type: state.config_manager.get_enum_setting(section, "language", enum_type),
        set_language_config,
    )

    return pystray.Menu(
        pystray.MenuItem("RPC Buttons", button_config_menu),
        pystray.MenuItem("RPC Language", language_config_menu),
    )
