from colorama import init, Fore, Style

from .enums import LogType


def log(text, type: LogType = LogType.Default):
    init()
    red_text = Fore.RED
    yellow_text = Fore.YELLOW
    blue_text = Fore.CYAN
    reset_text = Style.RESET_ALL

    if type == LogType.Notification:
        message_color = yellow_text
    elif type == LogType.Error:
        message_color = red_text
    elif type == LogType.Update_Status:
        message_color = blue_text
    else:
        message_color = reset_text

    print(f"{red_text}[YandexMusicRPC] -> {message_color}{text}{reset_text}")
