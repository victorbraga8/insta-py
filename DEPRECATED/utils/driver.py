from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import os, random

def criar_driver(headless: bool = False, profile_dir: str = "sessions/default", window_size: tuple[int,int] = (1366, 900), lang: str = "pt-BR", lat: float = -22.8268, lon: float = -43.0634, acc: int = 120):
    os.makedirs(profile_dir, exist_ok=True)
    w, h = window_size
    ua = os.getenv("USER_AGENT", "")
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--user-data-dir={os.path.abspath(profile_dir)}")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    opts.add_argument(f"--window-size={w},{h}")
    opts.add_argument("--disable-notifications")
    opts.add_argument(f"--lang={lang}")
    opts.add_argument("--password-store=basic")
    if ua:
        opts.add_argument(f"--user-agent={ua}")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    prefs = {"intl.accept_languages": lang, "profile.default_content_setting_values.geolocation": 1}
    opts.add_experimental_option("prefs", prefs)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=opts)
    driver.implicitly_wait(0)
    try:
        driver.execute_cdp_cmd("Browser.grantPermissions", {"origin": "https://www.instagram.com", "permissions": ["geolocation"]})
        driver.execute_cdp_cmd("Emulation.setGeolocationOverride", {"latitude": float(lat), "longitude": float(lon), "accuracy": int(acc)})
    except Exception:
        pass
    return driver
