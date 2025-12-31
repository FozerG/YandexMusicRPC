import time
from datetime import timedelta

import asyncio
import psutil
import pypresence

from .constants import CLIENT_ID_EN, CLIENT_ID_RU_DECLINED
from .enums import ButtonConfig, LanguageConfig, LogType, PlaybackStatus
from .logger import log
from .utils import Single_char, TrimString, build_buttons, format_duration
from .yandex_client import get_info
from .yandex_ws import get_current_track
from .error_handling import Handle_exception
from . import state
from pypresence import ActivityType


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
            client_id = CLIENT_ID_EN if state.language_config == LanguageConfig.ENGLISH else CLIENT_ID_RU_DECLINED
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
        state.needRestart = True

    @staticmethod
    def restart() -> None:
        Presence.currentTrack = None
        state.playable_id_prev = None
        if Presence.rpc:
            Presence.rpc.close()
            Presence.rpc = None
        time.sleep(3)
        Presence.discord_available()

    @staticmethod
    def discord_was_closed() -> None:
        log("Discord was closed. Waiting for restart...", LogType.Error)
        Presence.currentTrack = None
        state.playable_id_prev = None
        Presence.discord_available()

    @staticmethod
    def FullClearRPC() -> None:
        log("Clear RPC due to error", LogType.Error)
        Presence.currentTrack = None
        state.playable_id_prev = None
        if Presence.rpc:
            Presence.rpc.clear()

    @staticmethod
    def start() -> None:  # sourcery skip: low-code-quality
        clientErrorShown = False
        pausedTimestamp = 0

        Presence.discord_available()
        Presence.running = True
        Presence.currentTrack = None

        while Presence.running:
            if not Presence.client:
                if not clientErrorShown:
                    log(
                        "To work, you need to log in to your Yandex account. "
                        "Tray -> Yandex Settings -> Login to account.",
                        LogType.Error,
                    )
                    clientErrorShown = True

                    if not getattr(state, "login_auto_started", False):
                        state.login_auto_started = True

                        import threading
                        from .token_manager import Init_yaToken

                        threading.Thread(target=Init_yaToken, args=(True,), daemon=True).start()

                time.sleep(3)
                continue

            clientErrorShown = False
            currentTime = int(time.time())

            if not Presence.is_discord_running():
                Presence.discord_was_closed()

            if state.needRestart:
                state.needRestart = False
                Presence.restart()

            try:
                ongoing_track = Presence.getTrack()
                if ongoing_track["success"]:
                    is_new_track = Presence.currentTrack is None or Presence.currentTrack.get("label") != ongoing_track.get(
                        "label"
                    )
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
                        if Presence.paused_time > 5 * 60:
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
    def update_presence(ongoing_track, current_time: int = 0, paused: bool = False):
        start_time = current_time - int(ongoing_track["start-time"].total_seconds())
        end_time = start_time + ongoing_track["durationSec"]

        if state.language_config == LanguageConfig.RUSSIAN:
            playing_text = "Проигрывается"
            paused_text = "На паузе"
        else:
            playing_text = "Playing"
            paused_text = "On pause"

        presence_args = {
            "activity_type": ActivityType.LISTENING,
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

        if state.button_config != ButtonConfig.NEITHER:
            presence_args["buttons"] = build_buttons(ongoing_track["link"])

        Presence.rpc.update(**presence_args)

    @staticmethod
    def getTrack() -> dict:
        try:
            current_state = asyncio.run(get_current_track())
            if not (current_state and isinstance(current_state, dict) and current_state.get("success") is True):
                log("Failed to receive data from ynison.", LogType.Error)
                return {"success": False}

            current_playable_id = current_state["playable_id"]
            isNewTrack = state.playable_id_prev != current_playable_id

            if isNewTrack:
                track_info = get_info().get_track_by_id(current_state["playable_id"])
            else:
                track_info = state.info_cache

            if not (track_info and isinstance(track_info, dict) and track_info.get("success") is True):
                log("Failed to get track information.", LogType.Error)
                return {"success": False}

            state.playable_id_prev = current_playable_id
            state.info_cache = track_info

            name_current = ", ".join(track_info["artists"]) + " - " + track_info["title"]
            if isNewTrack:
                log(f'Now listening to "{name_current}" on device "{current_state["device_name"]}"')
            elif Presence.currentTrack and Presence.currentTrack.get("success"):
                currentTrack_copy = Presence.currentTrack.copy()
                currentTrack_copy["start-time"] = timedelta(milliseconds=int(current_state["progress_ms"]))
                currentTrack_copy["playback"] = PlaybackStatus.Paused if current_state["paused"] else PlaybackStatus.Playing
                return currentTrack_copy

            trackId = track_info["track_id"].split(":")
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
