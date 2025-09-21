# utils/driver.py
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options as ChromeOptions


def _build_chrome_options(
    *,
    headless: bool,
    window_size: Tuple[int, int],
    lang: str,
    user_agent: Optional[str],
    profile_dir: str,
    extra_args: Optional[Tuple[str, ...]] = None,
    prefs: Optional[Dict[str, Any]] = None,
) -> ChromeOptions:
    opts = ChromeOptions()

    profile_path = Path(profile_dir).resolve()
    profile_path.mkdir(parents=True, exist_ok=True)
    opts.add_argument(f"--user-data-dir={str(profile_path)}")

    if lang:
        opts.add_argument(f"--lang={lang}")
        opts.add_experimental_option("prefs", {"intl.accept_languages": lang})

    if user_agent:
        opts.add_argument(f"--user-agent={user_agent}")

    w, h = window_size
    opts.add_argument(f"--window-size={int(w)}x{int(h)}")

    if headless:
        opts.add_argument("--headless=new")

    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")
    opts.add_argument("--disable-default-apps")
    opts.add_argument("--disable-extensions")
    opts.add_argument("--disable-popup-blocking")
    opts.add_argument("--disable-notifications")
    opts.add_argument("--disable-features=Translate,NetworkServiceInProcess")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")

    opts.add_experimental_option(
        "excludeSwitches", ["enable-automation", "enable-logging"]
    )
    opts.add_experimental_option("useAutomationExtension", False)
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--log-level=3")
    opts.add_argument("--silent")

    if extra_args:
        for a in extra_args:
            opts.add_argument(a)

    merged_prefs = {
        "profile.default_content_setting_values.geolocation": 1,
        "profile.default_content_setting_values.notifications": 2,
    }
    if prefs:
        merged_prefs.update(prefs)
    opts.add_experimental_option("prefs", merged_prefs)

    chrome_binary = os.getenv("CHROME_BINARY", "").strip()
    if chrome_binary:
        opts.binary_location = chrome_binary

    return opts


def _apply_stealth_cdp(driver: webdriver.Chrome) -> None:
    try:
        driver.execute_cdp_cmd(
            "Page.addScriptToEvaluateOnNewDocument",
            {
                "source": """
                    Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                    window.chrome = window.chrome || {};
                    Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                    Object.defineProperty(navigator, 'languages', { get: () => ['pt-BR','pt','en-US','en'] });
                """
            },
        )
    except Exception:
        pass


def init_driver(
    *,
    headless: bool,
    window_size: Tuple[int, int] = (1280, 900),
    lang: str = "pt-BR",
    user_agent: Optional[str] = None,
    profile_dir: str,
    page_load_timeout: int = 60,
    script_timeout: int = 30,
    implicit_wait: float = 2.0,
    extra_args: Optional[Tuple[str, ...]] = None,
    prefs: Optional[Dict[str, Any]] = None,
) -> webdriver.Chrome:
    options = _build_chrome_options(
        headless=headless,
        window_size=window_size,
        lang=lang,
        user_agent=user_agent,
        profile_dir=profile_dir,
        extra_args=extra_args,
        prefs=prefs,
    )

    chromedriver_binary = os.getenv("CHROMEDRIVER_BINARY", "").strip()
    if chromedriver_binary:
        service = ChromeService(executable_path=chromedriver_binary, log_path="NUL")
    else:
        service = ChromeService(log_path="NUL")

    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.set_page_load_timeout(page_load_timeout)
    except Exception:
        pass
    try:
        driver.set_script_timeout(script_timeout)
    except Exception:
        pass
    try:
        driver.implicitly_wait(implicit_wait)
    except Exception:
        pass

    _apply_stealth_cdp(driver)
    return driver


def close_driver(driver: Optional[webdriver.Chrome], *, timeout: float = 3.0) -> None:
    if driver is None:
        return
    try:
        driver.quit()
    except Exception:
        try:
            driver.close()
        except Exception:
            try:
                driver.execute_cdp_cmd("Browser.close", {})
            except Exception:
                pass


def set_geolocation_override(
    driver: webdriver.Chrome, latitude: float, longitude: float, accuracy: int = 100
) -> bool:
    try:
        driver.execute_cdp_cmd(
            "Emulation.setGeolocationOverride",
            {
                "latitude": float(latitude),
                "longitude": float(longitude),
                "accuracy": int(accuracy),
            },
        )
        return True
    except Exception:
        return False


def ensure_window_size(driver: webdriver.Chrome, width: int, height: int) -> None:
    try:
        driver.set_window_size(int(width), int(height))
    except Exception:
        pass


def wait_for_page_ready(driver: webdriver.Chrome, timeout: float = 10.0) -> bool:
    try:
        end = time.time() + float(timeout)
        while time.time() < end:
            try:
                state = driver.execute_script("return document.readyState")
                if state == "complete":
                    return True
            except Exception:
                pass
            time.sleep(0.25)
    except Exception:
        pass
    return False
