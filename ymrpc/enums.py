from enum import Enum


class ButtonConfig(Enum):
    YANDEX_MUSIC_WEB = 1
    YANDEX_MUSIC_APP = 2
    BOTH = 3
    NEITHER = 4


class LanguageConfig(Enum):
    ENGLISH = 0
    RUSSIAN = 1


class PlaybackStatus(Enum):
    Paused = 0
    Playing = 1


class LogType(Enum):
    Default = 0
    Notification = 1
    Error = 2
    Update_Status = 3
