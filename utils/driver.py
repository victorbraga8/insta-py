import os
from pathlib import Path
from typing import Tuple, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

INSTAGRAM_ORIGIN = "https://www.instagram.com"


def criar_driver(
    headless: bool,
    profile_dir: str,
    window_size: Tuple[int, int],
    lang: str,
    geolocation: Optional[Tuple[float, float, int]],
):
    Path(profile_dir).mkdir(parents=True, exist_ok=True)
    opts = Options()
    if headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--user-data-dir={os.path.abspath(profile_dir)}")
    opts.add_argument(f"--window-size={window_size[0]},{window_size[1]}")
    opts.add_argument(f"--lang={lang}")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--no-sandbox")
    prefs = {
        "intl.accept_languages": lang,
        "profile.default_content_setting_values.geolocation": 1,
    }
    opts.add_experimental_option("prefs", prefs)
    service = Service()
    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(60)
    driver.set_script_timeout(30)
    driver.implicitly_wait(0)
    driver.get(INSTAGRAM_ORIGIN)
    if geolocation is not None:
        lat, lon, acc = geolocation
        try:
            driver.execute_cdp_cmd(
                "Browser.grantPermissions",
                {"origin": INSTAGRAM_ORIGIN, "permissions": ["geolocation"]},
            )
            driver.execute_cdp_cmd(
                "Emulation.setGeolocationOverride",
                {"latitude": float(lat), "longitude": float(lon), "accuracy": int(acc)},
            )
        except Exception:
            pass
    return driver
