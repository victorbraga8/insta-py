import os, threading, time
from pathlib import Path

# Fallback para load_dotenv se a lib não estiver instalada
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:

    def load_dotenv(path: str = ".env"):
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#") or "=" not in s:
                        continue
                    k, v = s.split("=", 1)
                    if k and k not in os.environ:
                        os.environ[k] = v
        except Exception:
            pass


from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from utils.driver import criar_driver
from utils.auth import ensure_login
from utils.collector import collect_for_tags
from utils.runner import run_actions

STOP = threading.Event()


def run_profile(profile_id: str, stop_event: threading.Event):
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
    profile_dir.mkdir(parents=True, exist_ok=True)

    driver = None
    try:
        driver = criar_driver(
            headless=headless,
            profile_dir=str(profile_dir),
            window_size=(ww, wh),
            lang=lang,
            geolocation=(lat, lon, acc),
        )

        ok = ensure_login(driver, user, pwd, str(profile_dir))
        if not ok or stop_event.is_set():
            return

        tags = [t.strip() for t in os.getenv("TAGS", "").split(",") if t.strip()]
        per_tag = int(os.getenv("PER_TAG", "30"))
        out_dir = os.getenv("OUT_DIR", "data/links")

        if tags and not stop_event.is_set():
            try:
                collect_for_tags(driver, tags, per_tag, out_dir, stop_event=stop_event)
            except (InvalidSessionIdException, WebDriverException):
                return

        if not stop_event.is_set():
            try:
                run_actions(driver, profile_id, stop_event=stop_event)
            except (InvalidSessionIdException, WebDriverException):
                return

        while not stop_event.is_set():
            try:
                driver.execute_script("return 1")
            except (InvalidSessionIdException, WebDriverException):
                break
            time.sleep(5)

    except KeyboardInterrupt:
        return
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            try:
                if getattr(driver, "service", None) and getattr(
                    driver.service, "process", None
                ):
                    driver.service.process.kill()
            except Exception:
                pass


def main():
    load_dotenv()

    profiles = [p.strip() for p in os.getenv("IG_PROFILES", "").split(",") if p.strip()]
    threads = []

    for pid in profiles:
        if not os.getenv(f"IG_{pid}_USER") or not os.getenv(f"IG_{pid}_PASS"):
            continue
        t = threading.Thread(target=run_profile, args=(pid, STOP), daemon=True)
        t.start()
        threads.append(t)

    if not threads:
        return

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        STOP.set()
        for t in threads:
            try:
                t.join(timeout=5)
            except Exception:
                pass


if __name__ == "__main__":
    main()
