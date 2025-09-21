import os
def _float_env(key:str, default:float)->float:
    try: return float(os.getenv(key,str(default)))
    except: return default

HUMAN_MIN = _float_env("HUMAN_DELAY_MIN", 2.0)
HUMAN_MAX = _float_env("HUMAN_DELAY_MAX", 5.0)
NAVIGATE_MIN = _float_env("NAVIGATE_DELAY_MIN", 3.0)
NAVIGATE_MAX = _float_env("NAVIGATE_DELAY_MAX", 6.0)
BETWEEN_TAGS_MIN = _float_env("BETWEEN_TAGS_MIN", 25.0)
BETWEEN_TAGS_MAX = _float_env("BETWEEN_TAGS_MAX", 60.0)
TYPING_MIN = _float_env("TYPING_MIN", 0.05)
TYPING_MAX = _float_env("TYPING_MAX", 0.15)
SCROLL_STEPS = int(os.getenv("SCROLL_STEPS", "7"))
SCROLL_MIN = _float_env("SCROLL_DELAY_MIN", 1.2)
SCROLL_MAX = _float_env("SCROLL_DELAY_MAX", 2.6)
WAIT_CLICK = int(os.getenv("WAIT_CLICK", "12"))
WAIT_PAGE = int(os.getenv("WAIT_PAGE", "15"))
