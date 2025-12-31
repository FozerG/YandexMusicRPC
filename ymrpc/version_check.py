import requests
from packaging import version

from .constants import CURRENT_VERSION
from .enums import LogType
from .logger import log


def GetLastVersion(repoUrl: str):
    try:
        response = requests.get(f"{repoUrl}/releases/latest", timeout=5)
        response.raise_for_status()
        latest_version = response.url.split("/")[-1]

        if version.parse(CURRENT_VERSION) < version.parse(latest_version):
            log(
                f"A new version has been released on GitHub. You are using - {CURRENT_VERSION}. "
                f"A new version - {latest_version}, you can download it at {repoUrl}/releases/tag/{latest_version}",
                LogType.Notification,
            )
        elif version.parse(CURRENT_VERSION) == version.parse(latest_version):
            log("You are using the latest version of the script")
        else:
            log("You are using the beta version of the script", LogType.Notification)

    except requests.exceptions.RequestException as e:
        log(f"Error getting latest version: {e}", LogType.Error)
