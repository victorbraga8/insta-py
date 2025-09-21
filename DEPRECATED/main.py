import os
from dotenv import load_dotenv
from utils.driver import criar_driver
from utils.login import realizar_login

def env_bool(key: str, default: str = "false") -> bool:
    return os.getenv(key, default).strip().lower() in ("1","true","yes","y")

if __name__ == "__main__":
    load_dotenv()
    user = os.getenv("IG_USER", "")
    pwd = os.getenv("IG_PASS", "")
    headless = env_bool("HEADLESS", "false")
    ww = int(os.getenv("WINDOW_WIDTH", "1366"))
    wh = int(os.getenv("WINDOW_HEIGHT", "900"))
    lang = os.getenv("LANG", "pt-BR")
    lat = float(os.getenv("GEO_LAT", "-22.8268"))
    lon = float(os.getenv("GEO_LON", "-43.0634"))
    acc = int(os.getenv("GEO_ACC", "120"))
    profile_dir = os.getenv("PROFILE_DIR", "sessions/default")
    driver = criar_driver(headless=headless, profile_dir=profile_dir, window_size=(ww, wh), lang=lang, lat=lat, lon=lon, acc=acc)
    try:
        if user and pwd:
            ok = realizar_login(driver, user, pwd)
        else:
            ok = False
        print("login_ok=", ok)
    finally:
        driver.quit()
