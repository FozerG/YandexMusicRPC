import contextlib
from config_manager import ConfigManager
from packaging import version
from datetime import timedelta
from yandex_music import Client, exceptions
from colorama import init, Fore, Style
from win32com.client import Dispatch  # Импортируем Dispatch для создания COM объекта

import aiohttp
from aiohttp import ClientConnectorError, ClientTimeout
import random
import string

import multiprocessing
import subprocess
import webbrowser
import pystray
import win32gui
import win32con
import win32console
import pypresence
import getToken
import keyring
import requests
import asyncio
import psutil
import json
import time
import re
import sys
import os
import winreg
import threading
import pythoncom
from enum import Enum
from PIL import Image

# Идентификатор клиента Discord для Rich Presence
CLIENT_ID_EN = "1269807014393942046"  # Yandex Music
CLIENT_ID_RU_DECLINED = "1269826362399522849"  # Яндекс Музыку (склонение для активности "Слушает")

# Версия (tag) скрипта для проверки на актуальность через Github Releases
CURRENT_VERSION = "v0.3.1"

# Ссылка на репозиторий
REPO_URL = "https://github.com/FozerG/YandexMusicRPC"

# Личный токен Яндекс.Музыки
# https://github.com/MarshalX/yandex-music-api/discussions/513
# - Авторизация в Яндексе необходима для получения текущего трека с его серверов.
ya_token = str()


# Флаг для настройки автозапуска с компьютером
auto_start_windows = False

# --------- Переменные ниже являются временными и не требуют изменения.
# Переменная для хранения предыдущего трека и избежания дублирования обновлений.
playable_id_prev = None
info_cache = dict()

# Переменная для хранения полного пути к иконке
icoPath = str()

# Очередь для передачи результатов между процессами
result_queue = multiprocessing.Queue()

# Переменная для проверки необходимости запуска рестарта в главном потоке Presence
needRestart = False

# Менеджер настроек
config_manager = ConfigManager()


class ButtonConfig(Enum):
    YANDEX_MUSIC_WEB = 1
    YANDEX_MUSIC_APP = 2
    BOTH = 3
    NEITHER = 4


class LanguageConfig(Enum):
    ENGLISH = 0
    RUSSIAN = 1


# Глобальные настройки для RPC. Загружаются из метода get_saves_settings()
button_config = None
language_config = None


class PlaybackStatus(Enum):
    Paused = 0
    Playing = 1


def extract_device_name(data):
    try:
        devices = data.get("devices", [])
        active_device_id = data.get("active_device_id_optional")

        return next(
            (device["info"]["title"] for device in devices if device["info"]["device_id"] == active_device_id),
            "Desktop",
        )
    except KeyError as e:
        return f"error: {e}"


def get_info():
    global ya_token

    class Info:
        def __init__(self, token):
            self.token = token

        @staticmethod
        def get_track_by_id(track_id):
            try:
                track = Presence.client.tracks([track_id])
                if not track or not track[0]:
                    log(f"Track with ID {track_id} not found.", LogType.Error)
                    return {"success": False}
                return {
                    "success": True,
                    "track_id": track[0].track_id,
                    "title": track[0].title,
                    "og-image": track[0].og_image,
                    "artists": [artist.name for artist in track[0].artists],
                    "album": track[0].albums[0].title if track[0].albums else None,
                }
            except Exception as e:
                log(f"Failed to fetch track info for ID {track_id}: {str(e)}", LogType.Error)
                return {"success": False}

    return Info(ya_token)


async def get_current_track() -> dict:
    global ya_token
    device_info = {"app_name": "Chrome", "type": 1}

    ws_proto = {
        "Ynison-Device-Id": "".join([random.choice(string.ascii_lowercase) for _ in range(16)]),
        "Ynison-Device-Info": json.dumps(device_info),
    }

    timeout = ClientTimeout(total=15, connect=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.ws_connect(
                url="wss://ynison.music.yandex.ru/redirector.YnisonRedirectService/GetRedirectToYnison",
                headers={
                    "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(ws_proto)}",
                    "Origin": "https://music.yandex.ru",
                    "Authorization": f"OAuth {ya_token}",
                },
                timeout=10,
            ) as ws:
                recv = await ws.receive()
                data = json.loads(recv.data)

            if "redirect_ticket" not in data or "host" not in data:
                log(f"Invalid response structure: {data}", LogType.Error)
                return {"success": False}

            new_ws_proto = ws_proto.copy()
            new_ws_proto["Ynison-Redirect-Ticket"] = data["redirect_ticket"]

            to_send = {
                "update_full_state": {
                    "player_state": {
                        "player_queue": {
                            "current_playable_index": -1,
                            "entity_id": "",
                            "entity_type": "VARIOUS",
                            "playable_list": [],
                            "options": {"repeat_mode": "NONE"},
                            "entity_context": "BASED_ON_ENTITY_BY_DEFAULT",
                            "version": {
                                "device_id": ws_proto["Ynison-Device-Id"],
                                "version": 9021243204784341000,
                                "timestamp_ms": 0,
                            },
                            "from_optional": "",
                        },
                        "status": {
                            "duration_ms": 0,
                            "paused": True,
                            "playback_speed": 1,
                            "progress_ms": 0,
                            "version": {
                                "device_id": ws_proto["Ynison-Device-Id"],
                                "version": 8321822175199937000,
                                "timestamp_ms": 0,
                            },
                        },
                    },
                    "device": {
                        "capabilities": {
                            "can_be_player": True,
                            "can_be_remote_controller": False,
                            "volume_granularity": 16,
                        },
                        "info": {
                            "device_id": ws_proto["Ynison-Device-Id"],
                            "type": "WEB",
                            "title": "Chrome Browser",
                            "app_name": "Chrome",
                        },
                        "volume_info": {"volume": 0},
                        "is_shadow": False,
                    },
                    "is_currently_active": False,
                },
                "rid": "ac281c26-a047-4419-ad00-e4fbfda1cba3",
                "player_action_timestamp_ms": 0,
                "activity_interception_type": "DO_NOT_INTERCEPT_BY_DEFAULT",
            }

            async with session.ws_connect(
                url=f"wss://{data['host']}/ynison_state.YnisonStateService/PutYnisonState",
                headers={
                    "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(new_ws_proto)}",
                    "Origin": "https://music.yandex.ru",
                    "Authorization": f"OAuth {ya_token}",
                },
                timeout=10,
                method="GET",
            ) as ws:
                await ws.send_str(json.dumps(to_send))
                recv = await asyncio.wait_for(ws.receive(), timeout=10)
                ynison = json.loads(recv.data)
                track_index = ynison["player_state"]["player_queue"]["current_playable_index"]
                if track_index == -1:
                    log("No track is currently playing.", LogType.Error)
                    return {"success": False}
                track = ynison["player_state"]["player_queue"]["playable_list"][track_index]

            await session.close()
            return {
                "device_name": extract_device_name(ynison),
                "paused": ynison["player_state"]["status"]["paused"],
                "duration_ms": ynison["player_state"]["status"]["duration_ms"],
                "progress_ms": ynison["player_state"]["status"]["progress_ms"],
                "entity_id": ynison["player_state"]["player_queue"]["entity_id"],
                "repeat_mode": ynison["player_state"]["player_queue"]["options"]["repeat_mode"],
                "entity_type": ynison["player_state"]["player_queue"]["entity_type"],
                "playable_id": track["playable_id"],
                "success": True,
            }

    except ClientConnectorError as e:
        log(f"Cannot connect to host: {e}. Please check your connection.", LogType.Error)
        return {"success": False}

    except asyncio.TimeoutError:
        log("Request timed out. Please check your connection.", LogType.Error)
        return {"success": False}

    except Exception as e:
        log(f"An unexpected error occurred: {str(e)}", LogType.Error)
        return {"success": False}
    finally:
        if session:
            await session.close()


class Presence:
    client = None
    currentTrack = None
    rpc = None
    running = False
    paused = False
    paused_time = 0
    exe_names = ["Discord.exe", "DiscordCanary.exe", "DiscordPTB.exe", "Vesktop.exe"]

    @staticmethod
    def is_discord_running() -> bool:
        return any(name in (p.name() for p in psutil.process_iter()) for name in Presence.exe_names)

    @staticmethod
    def connect_rpc():
        try:
            client_id = CLIENT_ID_EN if language_config == LanguageConfig.ENGLISH else CLIENT_ID_RU_DECLINED
            rpc = pypresence.Presence(client_id)
            rpc.connect()
            return rpc
        except pypresence.exceptions.DiscordNotFound:
            log("Pypresence - Discord not found.", LogType.Error)
            return None
        except pypresence.exceptions.InvalidID:
            log("Pypresence - Incorrect CLIENT_ID", LogType.Error)
            return None
        except Exception as e:
            log(f"Discord is not ready for a reason: {e}", LogType.Error)
            return None

    @staticmethod
    def discord_available():
        while True:
            if Presence.is_discord_running():
                Presence.rpc = Presence.connect_rpc()
                if Presence.rpc:
                    log("Discord is ready for Rich Presence")
                    break
                else:
                    log("Discord is launched but not ready for Rich Presence. Try again...", LogType.Error)
            else:
                log("Discord is not launched", LogType.Error)
            time.sleep(3)

    @staticmethod
    def stop() -> None:
        if Presence.rpc:
            Presence.rpc.close()
            Presence.rpc = None
            Presence.running = False

    @staticmethod
    def need_restart() -> None:
        log("Restarting RPC because settings have been changed...", LogType.Update_Status)
        global needRestart
        needRestart = True

    @staticmethod
    def restart() -> None:
        Presence.currentTrack = None
        global playable_id_prev
        playable_id_prev = None
        if Presence.rpc:
            Presence.rpc.close()
            Presence.rpc = None
        time.sleep(3)
        Presence.discord_available()

    @staticmethod
    def discord_was_closed() -> None:
        log("Discord was closed. Waiting for restart...", LogType.Error)
        Presence.currentTrack = None
        global playable_id_prev
        playable_id_prev = None
        Presence.discord_available()

    @staticmethod
    def FullClearRPC() -> None:
        log("Clear RPC due to error", LogType.Error)
        Presence.currentTrack = None
        global playable_id_prev
        playable_id_prev = None
        Presence.rpc.clear()

    # Метод для запуска Rich Presence.
    @staticmethod
    def start() -> None:  # sourcery skip: low-code-quality
        global ya_token
        global needRestart
        clientErrorShown = False
        Presence.discord_available()
        Presence.running = True
        Presence.currentTrack = None

        while Presence.running:
            if not Presence.client:
                if not clientErrorShown:
                    log(
                        "To work, you need to log in to your Yandex account. Tray -> Yandex Settings -> Login to "
                        "account.",
                        LogType.Error,
                    )
                    clientErrorShown = True
                time.sleep(3)
                continue
            clientErrorShown = False
            currentTime = int(time.time())
            if not Presence.is_discord_running():
                Presence.discord_was_closed()
            if needRestart:
                needRestart = False
                Presence.restart()

            try:
                ongoing_track = Presence.getTrack()
                if ongoing_track["success"]:
                    is_new_track = Presence.currentTrack is None or Presence.currentTrack.get(
                        "label"
                    ) != ongoing_track.get("label")
                    is_start_time_changed = Presence.currentTrack and Presence.currentTrack.get(
                        "start-time"
                    ) != ongoing_track.get("start-time")
                    is_paused = ongoing_track["playback"] != PlaybackStatus.Playing
                    is_playing = not is_paused
                    if is_new_track:
                        log(f"Changed track to {ongoing_track['label']}", LogType.Update_Status)
                        Presence.update_presence(ongoing_track, currentTime)
                        Presence.currentTrack = ongoing_track
                        Presence.paused = False
                        Presence.paused_time = 0

                    elif is_start_time_changed and not Presence.paused:
                        Presence.update_presence(ongoing_track, currentTime)
                        Presence.currentTrack = ongoing_track
                        Presence.paused = False
                        Presence.paused_time = 0

                    elif is_paused and not Presence.paused:
                        log(f"Track {ongoing_track['label']} on pause", LogType.Update_Status)
                        Presence.update_presence(ongoing_track, paused=True)
                        Presence.paused = True
                        pausedTimestamp = currentTime

                    elif is_playing and Presence.paused:
                        log(f"Track {ongoing_track['label']} off pause.", LogType.Update_Status)
                        Presence.update_presence(ongoing_track, currentTime)
                        Presence.paused = False
                        Presence.currentTrack = ongoing_track
                        pausedTimestamp = 0

                    if Presence.paused and pausedTimestamp != 0:
                        Presence.paused_time = currentTime - pausedTimestamp
                        if Presence.paused_time > 5 * 60:  # Если пауза больше 5 минут
                            Presence.rpc.clear()
                            pausedTimestamp = 0
                            log("Clear RPC due to paused for more than 5 minutes", LogType.Update_Status)
                    else:
                        Presence.paused_time = 0
                else:
                    Presence.FullClearRPC()
                time.sleep(3)
            except pypresence.exceptions.PipeClosed:
                Presence.discord_was_closed()
            except Exception as e:
                log(f"Presence class stopped for a reason: {e}", LogType.Error)

    @staticmethod
    def update_presence(ongoing_track, current_time=0, paused=False):
        start_time = current_time - int(ongoing_track["start-time"].total_seconds())
        end_time = start_time + ongoing_track["durationSec"]

        if language_config == LanguageConfig.RUSSIAN:
            playing_text = "Проигрывается"
            paused_text = "На паузе"
        else:
            playing_text = "Playing"
            paused_text = "On pause"

        presence_args = {
            "activity_type": 2,
            "details": ongoing_track["title"],
            "large_image": ongoing_track["og-image"],
            "small_image": (
                "https://github.com/FozerG/YandexMusicRPC/blob/main/assets/Paused.png?raw=true"
                if paused
                else "https://github.com/FozerG/YandexMusicRPC/blob/main/assets/Playing.png?raw=true"
            ),
            "small_text": paused_text if paused else playing_text,
        }

        if ongoing_track["artist"]:
            presence_args["state"] = ongoing_track["artist"]

        if ongoing_track["album"] != ongoing_track["title"]:
            presence_args["large_text"] = ongoing_track["album"]

        if paused:
            presence_args["large_text"] = (
                f"{paused_text} "
                f"{format_duration(int(ongoing_track['start-time'].total_seconds() * 1000))} / "
                f"{ongoing_track['formatted_duration']}"
            )
        else:
            presence_args["start"] = start_time
            presence_args["end"] = end_time

        if button_config != ButtonConfig.NEITHER:
            presence_args["buttons"] = build_buttons(ongoing_track["link"])

        Presence.rpc.update(**presence_args)

    # Метод для получения информации о текущем треке.
    @staticmethod
    def getTrack() -> dict:
        global playable_id_prev
        global info_cache
        try:
            current_state = asyncio.run(get_current_track())
            if not (current_state and isinstance(current_state, dict) and current_state.get('success') is True):
                log("Failed to receive data from ynison.", LogType.Error)
                return {"success": False}
            
            current_playable_id = current_state["playable_id"]
            isNewTrack = playable_id_prev != current_playable_id

            if isNewTrack:
                track_info = get_info().get_track_by_id(current_state["playable_id"])
            else:
                track_info = info_cache
                
            if not (track_info and isinstance(track_info, dict) and track_info.get('success') is True):
                log("Failed to get track information.", LogType.Error)
                return {"success": False}
            
            playable_id_prev = current_playable_id
            info_cache = track_info
            name_current = ", ".join(track_info["artists"]) + " - " + track_info["title"]
            if isNewTrack:
                log(f'Now listening to "{name_current}" on device "{current_state["device_name"]}"')
            # Если песня уже играет, просто вернем её с актуальным статусом паузы и позиции.
            elif Presence.currentTrack["success"]:
                currentTrack_copy = Presence.currentTrack.copy()
                currentTrack_copy["start-time"] = timedelta(milliseconds=int(current_state["progress_ms"]))
                currentTrack_copy["playback"] = (
                    PlaybackStatus.Paused if current_state["paused"] else PlaybackStatus.Playing
                )
                return currentTrack_copy

            trackId = track_info["track_id"].split(":")
            if track_info:
                duration_ms = int(current_state["duration_ms"])
                return {
                    "success": True,
                    "title": Single_char(TrimString(track_info["title"], 40)),
                    "artist": Single_char(TrimString(f"{', '.join(track_info['artists'])}", 40)),
                    "album": Single_char(TrimString(track_info["album"], 25)),
                    "label": TrimString(f"{', '.join(track_info['artists'])} - {track_info['title']}", 60),
                    "link": f"https://music.yandex.ru/album/{trackId[1]}/track/{trackId[0]}/",
                    "durationSec": duration_ms // 1000,
                    "formatted_duration": format_duration(duration_ms),
                    "start-time": timedelta(milliseconds=int(current_state["progress_ms"])),
                    "playback": PlaybackStatus.Paused if current_state["paused"] else PlaybackStatus.Playing,
                    "og-image": "https://" + track_info["og-image"][:-2] + "400x400",
                }
        except Exception as exception:
            Handle_exception(exception)
            return {"success": False}


def format_duration(duration_ms):
    total_seconds = duration_ms // 1000
    minutes = total_seconds // 60
    seconds = total_seconds % 60

    # Форматирование строки
    return f"{minutes}:{seconds:02}"


# ВНИМАНИЕ!
# ДЛЯ ТЕКСТА КНОПКИ ЕСТЬ ОГРАНИЧЕНИЕ В 32 БАЙТА. КИРИЛЛИЦА СЧИТАЕТСЯ ЗА 2 БАЙТА.
# ЕСЛИ ПРЕВЫСИТЬ ЛИМИТ ТО DISCORD RPC НЕ БУДЕТ ВИДЕН ДРУГИМ ПОЛЬЗОВАТЕЛЯМ!
def build_buttons(url):
    def create_button(label_en, label_ru, url_btn):
        label_lang = label_en if language_config == LanguageConfig.ENGLISH else label_ru
        return {"label": label_lang, "url": url_btn}

    buttons = []

    if button_config == ButtonConfig.YANDEX_MUSIC_WEB:
        buttons.append(create_button("Listen on Yandex Music", "Откр. в браузере", url))
    elif button_config == ButtonConfig.YANDEX_MUSIC_APP:
        deep_link = extract_deep_link(url)
        buttons.append(create_button("Listen on Yandex Music (in App)", "Откр. в прилож.", deep_link))
    elif button_config == ButtonConfig.BOTH:
        buttons.append(create_button("Listen on Yandex Music (Web)", "Откр. в браузере", url))
        deep_link = extract_deep_link(url)
        buttons.append(create_button("Listen on Yandex Music (App)", "Откр. в прилож.", deep_link))

    for button in buttons:
        label = button["label"]
        if len(label.encode("utf-8")) > 32:
            raise ValueError(f"Label '{label}' exceeds 32 bytes")
    return buttons


def extract_deep_link(url):
    pattern = r"https://music.yandex.ru/album/(\d+)/track/(\d+)"
    if match := re.match(pattern, url):
        album_id, track_id = match.groups()
        share_track_path = f"album/{album_id}/track/{track_id}"
        return f"yandexmusic://{share_track_path}"
    else:
        return None


def Handle_exception(exception):  # Обработка json ошибок из Yandex Music
    json_str = str(exception).replace("'", '"')
    if match := re.search(r"({.*?})", json_str):
        json_str = match[1]

    try:
        data = json.loads(json_str)
        if error_name := data.get("name"):
            if error_name == "Unavailable For Legal Reasons":
                log(
                    "You are using Yandex music in a country where it is not available without authorization! Turn "
                    "off VPN or login using a Yandex token.",
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


def WaitAndExit():
    if Is_run_by_exe():
        win32gui.ShowWindow(window, win32con.SW_SHOW)
    Presence.stop()
    input("Press Enter to close the program.")
    if Is_run_by_exe():
        win32gui.PostMessage(window, win32con.WM_CLOSE, 0, 0)
    else:
        sys.exit(0)


def TrimString(text, maxChars):
    return f"{text[:maxChars]}..." if len(text) > maxChars else text


def Single_char(s):
    return f'"{s}"' if len(s) == 1 else s


class LogType(Enum):
    Default = 0
    Notification = 1
    Error = 2
    Update_Status = 3


def log(text, type=LogType.Default):
    init()  # Инициализация colorama
    # Цвета текста
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


def GetLastVersion(repoUrl):
    try:
        global CURRENT_VERSION
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


# Функция для переключения состояния auto_start_windows
def toggle_auto_start_windows():
    global auto_start_windows
    auto_start_windows = not auto_start_windows
    log(f"Bool auto_start_windows set state: {auto_start_windows}")

    def create_shortcut(target, shortcut_path, description="", arguments=""):
        pythoncom.CoInitialize()  # Инициализируем COM библиотеки
        shell = Dispatch("WScript.Shell")  # Создаем объект для работы с ярлыками
        shortcut = shell.CreateShortcut(shortcut_path)  # Создаем ярлык
        shortcut.TargetPath = target  # Устанавливаем путь к исполняемому файлу
        shortcut.WorkingDirectory = os.path.dirname(target)  # Устанавливаем рабочую директорию
        shortcut.Description = description  # Устанавливаем описание ярлыка
        shortcut.Arguments = arguments
        shortcut.Save()  # Сохраняем ярлык

    def change_setting(
        tglle: bool,
    ):  # Выношу в отдельную функцию, чтобы иметь возможность запустить в отдельном потоке,
        # ДВА способа добавления в автозапуск.
        # Первый через добавление программы в папку автостарта.
        # Второй через изменение реестра.
        # Оба не требуют прав администратора.
        if tglle:
            try:
                # Получаем абсолютный путь к текущему исполняемому файлу
                exe_path = os.path.abspath(sys.argv[0])
                # Определяем путь для ярлыка в автозагрузке
                shortcut_path = os.path.join(
                    os.getenv("APPDATA"),
                    "Microsoft",
                    "Windows",
                    "Start Menu",
                    "Programs",
                    "Startup",
                    "YandexMusicRPC.lnk",
                )
                # Создаем ярлык в автозагрузке
                create_shortcut(exe_path, shortcut_path, arguments="--run-through-startup")
            except Exception:
                exe_path = f'"{os.path.abspath(sys.argv[0])}" --run-through-startup'
                # Открываем ключ реестра для автозапуска программ
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                    0,
                    winreg.KEY_SET_VALUE,
                )
                # Устанавливаем новый параметр в реестре с именем 'YandexMusicRPC' и значением пути к исполняемому файлу
                winreg.SetValueEx(key, "YandexMusicRPC", 0, winreg.REG_SZ, exe_path)
                winreg.CloseKey(key)  # Закрываем ключ реестра
        else:  # Удаляем оба метода
            # Удаляем ярлык из автозагрузки
            shortcut_path = os.path.join(
                os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "YandexMusicRPC.lnk"
            )
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            # Удаляем запись из реестра
            with contextlib.suppress(FileNotFoundError):
                key = winreg.OpenKey(
                    winreg.HKEY_CURRENT_USER,
                    r"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run",
                    0,
                    winreg.KEY_ALL_ACCESS,
                )
                winreg.DeleteValue(key, "YandexMusicRPC")
                winreg.CloseKey(key)

    # Запускаем в отдельном потоке для оптимизации
    threading.Thread(target=change_setting, args=[auto_start_windows]).start()


# Функция, которая при запуске программы проверяет, есть ли программа в автозапуске.
# Используется при подгрузке стартовых параметров
def is_in_autostart():
    def is_in_startup():
        shortcut_path = os.path.join(
            os.getenv("APPDATA"), "Microsoft", "Windows", "Start Menu", "Programs", "Startup", "YandexMusicRPC.lnk"
        )  # Определяем путь к ярлыку
        return os.path.exists(shortcut_path)  # Проверяем, существует ли ярлык в папке автозагрузки

    def is_in_registry():
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ
            )  # Открываем ключ реестра для чтения
            winreg.QueryValueEx(key, "YandexMusicRPC")  # Проверяем, существует ли параметр в реестре
            winreg.CloseKey(key)  # Закрываем ключ реестра
            return True
        except FileNotFoundError:
            return False  # Если параметр не найден, возвращаем False

    return is_in_startup() or is_in_registry()  # Возвращаем True, если программа присутствует в автозапуске


def toggle_console():
    if win32gui.IsWindowVisible(window):
        win32gui.ShowWindow(window, win32con.SW_HIDE)
    else:
        Show_Console_Permanent()


# Действия для кнопок
def tray_click(icon, query):
    match str(query):
        case "GitHub":
            webbrowser.open(REPO_URL, new=2)

        case "Exit":
            Presence.stop()
            icon.stop()
            win32gui.PostMessage(window, win32con.WM_CLOSE, 0, 0)


def get_account_name():
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


# Функция для загрузки сохраненных настроек. Если настройки отсутствуют, используются значения по умолчанию из fallback.
def get_saves_settings(fromStart=False):
    global button_config
    global language_config
    global auto_start_windows

    auto_start_windows = is_in_autostart()
    button_config = config_manager.get_enum_setting(
        "UserSettings", "buttons_settings", ButtonConfig, fallback=ButtonConfig.BOTH
    )
    language_config = config_manager.get_enum_setting(
        "UserSettings", "language", LanguageConfig, fallback=LanguageConfig.RUSSIAN
    )
    if fromStart:
        log(
            f"Loaded settings: {Style.RESET_ALL}button_config = {button_config.name}, "
            f"language_config = {language_config.name}",
            LogType.Update_Status,
        )


# Функция для создания меню на основе переданных параметров
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
    config_manager.set_enum_setting("UserSettings", "buttons_settings", value)
    log(f"Setting has been changed : buttons_settings to {value.name}")
    get_saves_settings()
    Presence.need_restart()


def set_language_config(value):
    value = convert_to_enum(LanguageConfig, value)
    config_manager.set_enum_setting("UserSettings", "language", value)
    log(f"Setting has been changed : language to {value.name}")
    get_saves_settings()
    Presence.need_restart()


# Функция для создания настроек меню RPC
def create_rpc_settings_menu():
    button_config_menu = create_enum_menu(
        ButtonConfig,
        lambda section, enum_type: config_manager.get_enum_setting(section, "buttons_settings", enum_type),
        set_button_config,
    )
    language_config_menu = create_enum_menu(
        LanguageConfig,
        lambda section, enum_type: config_manager.get_enum_setting(section, "language", enum_type),
        set_language_config,
    )

    return pystray.Menu(
        pystray.MenuItem("RPC Buttons", button_config_menu), pystray.MenuItem("RPC Language", language_config_menu)
    )


# Функция для обновления имени аккаунта в меню
def update_account_name(icon, new_account_name):
    rpcSettingsMenu = create_rpc_settings_menu()
    settingsMenu = pystray.Menu(
        pystray.MenuItem(f"Logged in as - {new_account_name}", lambda: None, enabled=False),
        pystray.MenuItem("Login to account...", lambda: Init_yaToken(True)),
    )

    icon.menu = pystray.Menu(
        pystray.MenuItem("Hide/Show Console", toggle_console, default=True),
        pystray.MenuItem("Start with Windows", toggle_auto_start_windows, checked=lambda item: auto_start_windows),
        pystray.MenuItem("Yandex settings", settingsMenu),
        pystray.MenuItem("RPC settings", rpcSettingsMenu),
        pystray.MenuItem("GitHub", tray_click),
        pystray.MenuItem("Exit", tray_click),
    )


# Функция для создания иконки с меню
def create_tray_icon():
    tray_image = Image.open(Get_IconPath())
    account_name = get_account_name()
    rpcSettingsMenu = create_rpc_settings_menu()

    settingsMenu = pystray.Menu(
        pystray.MenuItem(f"Logged in as - {account_name}", lambda: None, enabled=False),
        pystray.MenuItem("Login to account...", lambda: Init_yaToken(True)),
    )

    return pystray.Icon(
        "YandexMusicRPC",
        tray_image,
        "YandexMusicRPC",
        menu=pystray.Menu(
            pystray.MenuItem("Hide/Show Console", toggle_console, default=True),
            pystray.MenuItem("Start with Windows", toggle_auto_start_windows, checked=lambda item: auto_start_windows),
            pystray.MenuItem("Yandex settings", settingsMenu),
            pystray.MenuItem("RPC settings", rpcSettingsMenu),
            pystray.MenuItem("GitHub", tray_click),
            pystray.MenuItem("Exit", tray_click),
        ),
    )


# Функция для запуска иконки в отдельном потоке
def tray_thread(icon):
    icon.run()


def Is_already_running():
    return bool(win32gui.FindWindow(None, "YandexMusicRPC - Console"))


def Is_windows_11():
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
    win32gui.ShowWindow(window, win32con.SW_RESTORE)
    win32gui.SetForegroundWindow(window)


def Check_run_by_startup():
    # Если приложение запущено через автозагрузку, скрываем окно консоли сразу.
    # Если приложение запущено вручную, показываем окно консоли на 3 секунды и затем сворачиваем.
    if window:
        if "--run-through-startup" not in sys.argv:
            Show_Console_Permanent()
            log("Minimize to system tray in 3 seconds...")
            time.sleep(3)
        win32gui.ShowWindow(window, win32con.SW_HIDE)
    else:
        log("Console window not found", LogType.Error)


def Run_by_startup_without_conhost():
    if console_window := win32console.GetConsoleWindow():
        if "--run-through-startup" in sys.argv:
            win32gui.ShowWindow(console_window, win32con.SW_HIDE)
    else:
        log("Console window not found", LogType.Error)


def Disable_close_button():
    if hwnd := win32console.GetConsoleWindow():
        if hMenu := win32gui.GetSystemMenu(hwnd, False):
            win32gui.DeleteMenu(hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND)


def Set_ConsoleMode():
    hStdin = win32console.GetStdHandle(win32console.STD_INPUT_HANDLE)
    mode = hStdin.GetConsoleMode()
    # Отключить ENABLE_QUICK_EDIT_MODE, чтобы запретить выделение текста
    new_mode = mode & ~0x0040
    hStdin.SetConsoleMode(new_mode)


def Is_run_by_exe():
    script_path = os.path.abspath(sys.argv[0])
    return bool(script_path.endswith(".exe"))


def contains_non_latin_chars(s):
    # Проверяет, содержит ли строка символы, отличные от английских букв, цифр и стандартных знаков пунктуации.
    allowed_chars = string.ascii_letters + string.digits + string.punctuation + " "
    return any(char not in allowed_chars for char in s)


def Blur_string(s: str) -> str:
    if s is None:
        return ""
    return s if len(s) <= 8 else s[:4] + "*" * (len(s) - 8) + s[-4:]


def Remove_yaToken_From_Memory():
    if keyring.get_password("WinYandexMusicRPC", "token") is not None:
        keyring.delete_password("WinYandexMusicRPC", "token")
        log("Old token has been removed from memory.", LogType.Update_Status)
        global ya_token
        ya_token = str()


def update_token_task(icon_path, queue):
    result = getToken.get_yandex_music_token(icon_path)
    queue.put(result)


def Init_yaToken(forceGet=False):
    global ya_token
    token = str()

    if forceGet:
        try:
            Remove_yaToken_From_Memory()
            process = multiprocessing.Process(target=update_token_task, args=(Get_IconPath(), result_queue))
            process.start()
            process.join()
            token = result_queue.get()
            if token is not None and len(token) > 10:
                keyring.set_password("WinYandexMusicRPC", "token", token)
                log(f"Successfully received the token: {Blur_string(token)}", LogType.Update_Status)
        except Exception as exception:
            log(f"Something happened when trying to initialize token: {exception}", LogType.Error)
        finally:
            Presence.need_restart()
    elif ya_token:
        token = ya_token
        log(f"Loaded token from script: {Blur_string(token)}", LogType.Update_Status)

    else:
        try:
            token = keyring.get_password("WinYandexMusicRPC", "token")
            if token:
                log(f"Loaded token: {Blur_string(token)}", LogType.Update_Status)
        except Exception as exception:
            log(f"Something happened when trying to initialize token: {exception}", LogType.Error)
    if token is not None and len(token) > 10:
        ya_token = token
        try:
            Presence.client = Client(token=ya_token).init()
            log(f"Logged in as - {get_account_name()}", LogType.Update_Status)
            if Is_run_by_exe():
                update_account_name(mainMenu, get_account_name())
        except Exception as exception:
            Presence.client = None
            Handle_exception(exception)
    else:
        Presence.client = None

    if not Presence.client:
        log("Couldn't get the token. Try again.", LogType.Default)


def Get_IconPath():
    try:
        if getattr(sys, "frozen", False):
            # Если скрипт был запущен с использованием PyInstaller
            resources_path = sys._MEIPASS
        else:
            # Если скрипт запущен напрямую
            resources_path = os.path.dirname(os.path.realpath(__file__))

        return f"{resources_path}/assets/YMRPC_ico.ico"
    except Exception:
        return None


if __name__ == "__main__":
    multiprocessing.freeze_support()
    try:
        if Is_run_by_exe():
            Check_conhost()
            Set_ConsoleMode()
            log("Launched. Check the actual version...")
            GetLastVersion(REPO_URL)
            # Загрузка настроек
            get_saves_settings(True)
            # Запуск потока для трея
            mainMenu = create_tray_icon()
            icon_thread = threading.Thread(target=tray_thread, args=(mainMenu,))
            icon_thread.daemon = True
            icon_thread.start()

            # Получение окна консоли
            window = win32console.GetConsoleWindow()

            if Is_already_running():
                log("YandexMusicRPC is already running.", LogType.Error)
                Show_Console_Permanent()
                WaitAndExit()

            # Установка заголовка окна консоли
            win32console.SetConsoleTitle("YandexMusicRPC - Console")

            # Отключение кнопки закрытия консоли
            Disable_close_button()
            Check_run_by_startup()
        else:  # Запуск без exe (например в visual studio code)
            get_saves_settings(True)  # Загрузка настроек
            log("Launched without minimizing to tray and other and other gui functions")

        # Проверка наличия токена в памяти
        Init_yaToken(False)

        if contains_non_latin_chars(os.path.abspath(sys.argv[0])):
            log(
                f"Unsupported symbols were found in the program path. Please move the script to the correct path. "
                f"Current path:{os.path.abspath(sys.argv[0])}",
                LogType.Error,
            )

        # Запуск Presence
        Presence.start()

    except KeyboardInterrupt:
        log("Keyboard interrupt received, stopping...")
        Presence.stop()
