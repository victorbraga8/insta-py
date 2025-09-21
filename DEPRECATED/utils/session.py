import json, os
from typing import Dict, Any

SESSION_PATH = os.getenv("IG_SESSION_FILE", "data/session.json")


def load_session(driver, url="https://www.instagram.com/"):
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    if not os.path.exists(SESSION_PATH):
        return False
    with open(SESSION_PATH, "r", encoding="utf-8") as f:
        data: Dict[str, Any] = json.load(f)
    driver.get(url)
    for c in data.get("cookies", []):
        if "sameSite" in c and c["sameSite"] not in ("Strict", "Lax", "None"):
            c.pop("sameSite", None)
        driver.add_cookie(c)
    driver.refresh()
    for k, v in data.get("localStorage", {}).items():
        driver.execute_script(
            "window.localStorage.setItem(arguments[0], arguments[1]);", k, v
        )
    driver.get(url)
    return True


def save_session(driver):
    os.makedirs(os.path.dirname(SESSION_PATH), exist_ok=True)
    cookies = driver.get_cookies()
    ls_keys = driver.execute_script("return Object.keys(window.localStorage);")
    ls = {
        k: driver.execute_script("return window.localStorage.getItem(arguments[0]);", k)
        for k in ls_keys
    }
    with open(SESSION_PATH, "w", encoding="utf-8") as f:
        json.dump({"cookies": cookies, "localStorage": ls}, f, ensure_ascii=False)
