import re
import string

from .enums import ButtonConfig, LanguageConfig


def format_duration(duration_ms: int) -> str:
    total_seconds = duration_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60
    return f"{minutes}:{seconds:02}"


def TrimString(text: str, maxChars: int) -> str:
    return f"{text[:maxChars]}..." if len(text) > maxChars else text


def Single_char(s: str) -> str:
    return f'"{s}"' if len(s) == 1 else s


def extract_deep_link(url: str):
    pattern = r"https://music.yandex.ru/album/(\d+)/track/(\d+)"
    if match := re.match(pattern, url):
        album_id, track_id = match.groups()
        share_track_path = f"album/{album_id}/track/{track_id}"
        return f"yandexmusic://{share_track_path}"
    return None


def build_buttons(url: str):
    from . import state

    def create_button(label_en: str, label_ru: str, url_btn: str):
        label_lang = label_en if state.language_config == LanguageConfig.ENGLISH else label_ru
        return {"label": label_lang, "url": url_btn}

    buttons = []

    if state.button_config == ButtonConfig.YANDEX_MUSIC_WEB:
        buttons.append(create_button("Listen on Yandex Music", "Откр. в браузере", url))
    elif state.button_config == ButtonConfig.YANDEX_MUSIC_APP:
        deep_link = extract_deep_link(url)
        buttons.append(create_button("Listen on Yandex Music (in App)", "Откр. в прилож.", deep_link))
    elif state.button_config == ButtonConfig.BOTH:
        buttons.append(create_button("Listen on Yandex Music (Web)", "Откр. в браузере", url))
        deep_link = extract_deep_link(url)
        buttons.append(create_button("Listen on Yandex Music (App)", "Откр. в прилож.", deep_link))

    for button in buttons:
        label = button["label"]
        if len(label.encode("utf-8")) > 32:
            raise ValueError(f"Label '{label}' exceeds 32 bytes")

    return buttons

def Blur_string(s: str) -> str:
    if s is None:
        return ""
    return s if len(s) <= 8 else s[:4] + "*" * (len(s) - 8) + s[-4:]
