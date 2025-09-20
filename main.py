import os, threading, time
from pathlib import Path
from dotenv import load_dotenv
from utils.driver import criar_driver
from utils.auth import ensure_login


def run_profile(profile_id: str):
    user = os.getenv(f"IG_{profile_id}_USER", "")
    pwd = os.getenv(f"IG_{profile_id}_PASS", "")
    if not user or not pwd:
        return
    headless = os.getenv("HEADLESS", "false").lower() == "true"
    ww = int(os.getenv("WINDOW_WIDTH", "1366"))
    wh = int(os.getenv("WINDOW_HEIGHT", "900"))
    lang = os.getenv("LANG", "pt-BR")
    lat = float(os.getenv("GEO_LAT", "-22.8268"))
    lon = float(os.getenv("GEO_LON", "-43.0634"))
    acc = int(os.getenv("GEO_ACC", "120"))
    profile_dir = Path("sessions") / profile_id
    driver = criar_driver(
        headless=headless,
        profile_dir=str(profile_dir),
        window_size=(ww, wh),
        lang=lang,
        geolocation=(lat, lon, acc),
    )
    ok = ensure_login(driver, user, pwd, str(profile_dir))
    if not ok:
        try:
            driver.quit()
        except Exception:
            pass
        return
    try:
        while True:
            driver.execute_script("return 1")
            time.sleep(5)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def main():
    load_dotenv()
    profiles = [p.strip() for p in os.getenv("IG_PROFILES", "").split(",") if p.strip()]
    threads = []
    for pid in profiles:
        if not os.getenv(f"IG_{pid}_USER") or not os.getenv(f"IG_{pid}_PASS"):
            continue
        t = threading.Thread(target=run_profile, args=(pid,), daemon=True)
        t.start()
        threads.append(t)
    if not threads:
        return
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
