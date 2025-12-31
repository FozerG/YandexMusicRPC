import asyncio
import json
import random
import string

import aiohttp
from aiohttp import ClientConnectorError, ClientTimeout

from .enums import LogType
from .logger import log
from . import state


def extract_device_name(data: dict) -> str:
    try:
        devices = data.get("devices", [])
        active_device_id = data.get("active_device_id_optional")

        return next(
            (device["info"]["title"] for device in devices if device["info"]["device_id"] == active_device_id),
            "Desktop",
        )
    except KeyError as e:
        return f"error: {e}"


async def get_current_track() -> dict:
    device_info = {"app_name": "Chrome", "type": 1}

    ws_proto = {
        "Ynison-Device-Id": "".join([random.choice(string.ascii_lowercase) for _ in range(16)]),
        "Ynison-Device-Info": json.dumps(device_info),
    }

    timeout = ClientTimeout(total=15, connect=10)
    session = None

    try:
        session = aiohttp.ClientSession(timeout=timeout)

        async with session.ws_connect(
            url="wss://ynison.music.yandex.ru/redirector.YnisonRedirectService/GetRedirectToYnison",
            headers={
                "Sec-WebSocket-Protocol": f"Bearer, v2, {json.dumps(ws_proto)}",
                "Origin": "https://music.yandex.ru",
                "Authorization": f"OAuth {state.ya_token}",
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
                "Authorization": f"OAuth {state.ya_token}",
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
        if session is not None:
            await session.close()
