# utils/driver.py
# Cria/configura o Chrome, aplica anti-detecção, fixa geolocalização (São Gonçalo/RJ),
# persiste sessão por perfil e garante login. Tudo com defaults internos — a .env é opcional.
#
# Requisitos:
#   pip install selenium>=4.20

import os
import time
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


INSTAGRAM_URL = "https://www.instagram.com/"


# -------------------------
# Helpers de .env (com defaults fortes)
# -------------------------
def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key, str(default)).strip().lower()
    return v in ("1", "true", "yes", "y", "on")


def _env_int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)).strip())
    except Exception:
        return default


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, str(default)).strip())
    except Exception:
        return default


# -------------------------
# Driver factory
# -------------------------
def init_driver(profile_id: str, sessions_dir: str):
    """
    Retorna um webdriver.Chrome configurado:
      - user-data-dir por perfil (persistência de sessão)
      - idioma e user-agent
      - anti-detecção básica (remove navigator.webdriver, desabilita extensões de automation)
      - geolocalização de São Gonçalo via CDP + permissão de geolocation
    Todos os parâmetros têm defaults internos. A .env pode sobrescrever se existir.
    """
    # Defaults consolidados (podem ser sobrescritos por .env)
    headless = _env_bool("HEADLESS", False)
    lang = os.getenv("LANG", "pt-BR")
    ua = os.getenv(
        "USER_AGENT",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36",
    )
    ww = _env_int("WINDOW_WIDTH", 1366)
    wh = _env_int("WINDOW_HEIGHT", 900)
    stealth_mode = _env_bool("STEALTH_MODE", True)
    block_webrtc = _env_bool("BLOCK_WEBRTC_LEAKS", True)

    enable_geo = _env_bool("ENABLE_GEO", True)
    geo_lat = _env_float("GEO_LAT", -22.8268)
    geo_lon = _env_float("GEO_LON", -43.0634)
    geo_acc = _env_int("GEO_ACC", 120)

    nav_timeout_ms = _env_int("NAVIGATION_TIMEOUT_MS", 35000)

    # Pasta de sessão do perfil
    user_data_root = Path(sessions_dir).resolve()
    user_data_root.mkdir(parents=True, exist_ok=True)
    user_data_dir = user_data_root / profile_id
    user_data_dir.mkdir(parents=True, exist_ok=True)

    # Chrome Options
    options = ChromeOptions()
    options.add_argument(f"--user-data-dir={str(user_data_dir)}")
    options.add_argument("--profile-directory=Default")
    options.add_argument(f"--lang={lang}")
    options.add_argument(f"user-agent={ua}")
    options.add_argument(f"--window-size={ww},{wh}")

    if headless:
        options.add_argument("--headless=new")

    # Anti-detecção
    if stealth_mode:
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

    # Estabilidade em ambientes Windows/Linux
    options.add_argument("--disable-features=IsolateOrigins,site-per-process")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")

    # Preferências (idioma + mitigação WebRTC)
    prefs = {"intl.accept_languages": lang}
    if block_webrtc:
        prefs.update(
            {
                "webrtc.ip_handling_policy": "disable_non_proxied_udp",
                "webrtc.multiple_routes_enabled": False,
                "webrtc.nonproxied_udp_enabled": False,
            }
        )
    options.add_experimental_option("prefs", prefs)

    # Inicializa o Chrome
    driver = webdriver.Chrome(options=options, service=ChromeService())
    driver.set_page_load_timeout(max(5, int(nav_timeout_ms / 1000)))

    # Remover navigator.webdriver
    if stealth_mode:
        try:
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                },
            )
        except Exception:
            pass

    # Aplica geolocalização simulada + permissão
    if enable_geo:
        _apply_geo(driver, geo_lat, geo_lon, geo_acc)

    # Navega até a home para fixar overrides
    try:
        driver.get(INSTAGRAM_URL)
        # Reaplica após o primeiro load (alguns builds só aceitam depois do primeiro navigate)
        if stealth_mode:
            try:
                driver.execute_cdp_cmd(
                    "Page.addScriptToEvaluateOnNewDocument",
                    {
                        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
                    },
                )
            except Exception:
                pass
        if enable_geo:
            _apply_geo(driver, geo_lat, geo_lon, geo_acc)
    except Exception:
        time.sleep(2)
        driver.get(INSTAGRAM_URL)
        if enable_geo:
            _apply_geo(driver, geo_lat, geo_lon, geo_acc)

    return driver


def _apply_geo(driver, lat: float, lon: float, acc: float):
    """Aplica spoof de geolocalização + concede permissão para instagram.com."""
    try:
        driver.execute_cdp_cmd(
            "Emulation.setGeolocationOverride",
            {
                "latitude": float(lat),
                "longitude": float(lon),
                "accuracy": float(acc),
            },
        )
        driver.execute_cdp_cmd(
            "Browser.grantPermissions",
            {"origin": "https://www.instagram.com", "permissions": ["geolocation"]},
        )
    except Exception:
        # Em alguns ambientes, só funciona após primeiro .get()
        pass


# -------------------------
# Login
# -------------------------
def ensure_login(driver, username: str, password: str, wait_seconds: int = 35):
    """
    Fluxo mínimo:
      1) Se já estiver logado, retorna.
      2) Fecha cookie banner.
      3) Preenche credenciais e envia.
      4) Aguarda feed / valida sessão.
      5) Fecha modais pós-login.
    """
    wait = WebDriverWait(driver, wait_seconds)

    try:
        if _is_logged_in(driver, wait):
            return
    except Exception:
        pass

    _dismiss_cookies_if_any(driver)

    if "instagram.com" not in driver.current_url:
        driver.get(INSTAGRAM_URL)
        _dismiss_cookies_if_any(driver)

    # Campos (resilientes)
    selectors_user = [
        (By.NAME, "username"),
        (By.CSS_SELECTOR, "input[name='username']"),
        (By.CSS_SELECTOR, "input[type='text']"),
    ]
    selectors_pass = [
        (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[name='password']"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ]
    login_btns = [
        (By.CSS_SELECTOR, "button[type='submit']"),
        (By.XPATH, "//button/div[text()='Log in']/.."),
        (By.XPATH, "//button/div[text()='Entrar']/.."),
    ]

    user_input = None
    pw_input = None

    for how, sel in selectors_user:
        try:
            user_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((how, sel))
            )
            break
        except Exception:
            continue
    for how, sel in selectors_pass:
        try:
            pw_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((how, sel))
            )
            break
        except Exception:
            continue

    if not user_input or not pw_input:
        if _is_logged_in(driver, wait):
            return
        raise RuntimeError("Não foi possível localizar campos de login do Instagram.")

    try:
        user_input.clear()
        user_input.send_keys(username)
        time.sleep(0.25)
        pw_input.clear()
        pw_input.send_keys(password)
        time.sleep(0.25)
    except Exception:
        pass

    clicked = False
    for how, sel in login_btns:
        try:
            btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((how, sel))
            )
            btn.click()
            clicked = True
            break
        except Exception:
            continue

    if not clicked:
        try:
            pw_input.submit()
            clicked = True
        except Exception:
            pass

    if not _wait_feed_loaded(driver, wait):
        if not _is_logged_in(driver, wait):
            raise RuntimeError("Falha ao efetuar login no Instagram.")

    _dismiss_post_login_modals(driver)


# -------------------------
# Auxiliares de estado/login
# -------------------------
def _is_logged_in(driver, wait: WebDriverWait) -> bool:
    """Heurística: presença do nav/feed ou avatar indica sessão válida."""
    try:
        wait.until(
            EC.presence_of_element_located(
                (
                    By.CSS_SELECTOR,
                    "svg[aria-label*='Home'], svg[aria-label*='Página inicial'], nav a[href='/']",
                )
            )
        )
        return True
    except Exception:
        pass
    try:
        driver.find_element(By.CSS_SELECTOR, "img[alt*='profile'], img[alt*='perfil']")
        return True
    except Exception:
        return False


def _wait_feed_loaded(driver, wait: WebDriverWait, timeout: int = 25) -> bool:
    try:
        WebDriverWait(driver, timeout).until(
            EC.any_of(
                EC.presence_of_element_located((By.CSS_SELECTOR, "article")),
                EC.presence_of_element_located((By.CSS_SELECTOR, "nav")),
            )
        )
        return True
    except Exception:
        return False


def _dismiss_cookies_if_any(driver):
    candidates = [
        (By.XPATH, "//button[contains(., 'Permitir todos')]"),
        (By.XPATH, "//button[contains(., 'Aceitar todos')]"),
        (By.XPATH, "//button[contains(., 'Accept all')]"),
        (By.XPATH, "//button[contains(., 'Allow all')]"),
        (By.XPATH, "//button[contains(., 'Only allow essential')]"),
        (By.XPATH, "//button[contains(., 'Apenas essenciais')]"),
    ]
    for how, sel in candidates:
        try:
            btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((how, sel)))
            btn.click()
            time.sleep(0.3)
            break
        except Exception:
            continue


def _dismiss_post_login_modals(driver):
    candidates = [
        (By.XPATH, "//button[contains(., 'Agora não')]"),
        (By.XPATH, "//button[contains(., 'Not now')]"),
        (
            By.CSS_SELECTOR,
            "div[role='dialog'] button[aria-label*='Fechar'], div[role='dialog'] svg[aria-label*='Close']",
        ),
    ]
    for how, sel in candidates:
        try:
            btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((how, sel)))
            btn.click()
            time.sleep(0.2)
        except Exception:
            continue
