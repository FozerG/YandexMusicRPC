import json
import re

from .enums import LogType
from .logger import log


def Handle_exception(exception):
    json_str = str(exception).replace("'", '"')
    if match := re.search(r"({.*?})", json_str):
        json_str = match[1]

    try:
        data = json.loads(json_str)
        error_name = data.get("name")
        if error_name:
            if error_name == "Unavailable For Legal Reasons":
                log(
                    "You are using Yandex music in a country where it is not available without authorization! "
                    "Turn off VPN or login using a Yandex token.",
                    LogType.Error,
                )
            elif error_name == "session-expired":
                log("Your Yandex token is out of date or incorrect, login again.", LogType.Error)
            else:
                log(f"Something happened: {exception}", LogType.Error)
        else:
            log(f"Something happened: {exception}", LogType.Error)
    except Exception:
        log(f"Something happened: {exception}", LogType.Error)
