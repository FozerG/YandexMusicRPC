from .enums import LogType
from .logger import log
from . import state


def get_info():
    class Info:
        def __init__(self, token: str):
            self.token = token

        @staticmethod
        def get_track_by_id(track_id: str):
            try:
                from .presence import Presence

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

    return Info(state.ya_token)
