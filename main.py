import os, threading, time
from pathlib import Path
from dotenv import load_dotenv
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from utils.driver import criar_driver
from utils.auth import ensure_login
from utils.collector import collect_for_tags
from utils.runner import run_actions

# Flag global para encerramento gracioso
STOP = threading.Event()


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
        if not ok:
            return

        tags = [t.strip() for t in os.getenv("TAGS", "").split(",") if t.strip()]
        per_tag = int(os.getenv("PER_TAG", "30"))
        out_dir = os.getenv("OUT_DIR", "data/links")

        # Coleta (opcional)
        if tags and not STOP.is_set():
            try:
                collect_for_tags(driver, tags, per_tag, out_dir)
            except (InvalidSessionIdException, WebDriverException):
                # sessão caiu durante a coleta
                return

        # Execução das ações
        if not STOP.is_set():
            try:
                run_actions(driver, profile_id)
            except (InvalidSessionIdException, WebDriverException):
                # sessão caiu durante as ações
                return

        # Keep-alive controlado (para futura evolução/monitoramento)
        while not STOP.is_set():
            try:
                # ping leve — se o driver caiu, isso vai lançar exceção e sair
                driver.execute_script("return 1")
            except (InvalidSessionIdException, WebDriverException):
                break
            time.sleep(5)

    except KeyboardInterrupt:
        # Interrompido pelo usuário
        return
    finally:
        try:
            if driver is not None:
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

    try:
        # Aguarda as threads normalmente
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        # Sinaliza parada e espera threads encerrarem limpo
        STOP.set()
        for t in threads:
            try:
                t.join(timeout=5)
            except Exception:
                pass


if __name__ == "__main__":
    main()
