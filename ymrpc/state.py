import multiprocessing
from .config_manager import ConfigManager

# Runtime globals (kept intentionally to preserve original behavior).
ya_token = str()
auto_start_windows = False
login_auto_started = False

playable_id_prev = None
info_cache = dict()
icoPath = str()

result_queue = multiprocessing.Queue()
needRestart = False

config_manager = ConfigManager()

button_config = None
language_config = None

# Windows handles / objects (assigned at runtime).
window = None
mainMenu = None
