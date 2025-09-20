import os, json, time, random
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException,
    ElementClickInterceptedException,
)

LOGIN_URL = "https://www.instagram.com/accounts/login/?next=/"
HOME_URL = "https://www.instagram.com/"

TYPE_MIN = int(os.getenv("TYPE_MIN_MS", "45"))
TYPE_MAX = int(os.getenv("TYPE_MAX_MS", "120"))
TYPE_ERR = float(os.getenv("TYPE_MISTAKE_PROB", "0.02"))
POST_TYPE_PAUSE = int(os.getenv("POST_TYPE_PAUSE_MS", "350"))


def _click(driver, el):
    try:
        el.click()
    except ElementClickInterceptedException:
        driver.execute_script("arguments[0].click();", el)


def _dismiss(driver):
    for xp in [
        "//button[.='Aceitar' or .='Allow all' or .='Accept' or .='Permitir todos']",
        "//button[.='Only allow essential' or .='Apenas essenciais']",
        "//div[@role='dialog']//button[.='Agora não' or .='Not now']",
    ]:
        try:
            btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.XPATH, xp))
            )
            _click(driver, btn)
            time.sleep(0.35)
        except Exception:
            pass


def _already_logged(driver):
    try:
        WebDriverWait(driver, 4).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//nav//a[contains(@href,'/explore/')] | //a[contains(@href,'/accounts/edit')]",
                )
            )
        )
        return True
    except TimeoutException:
        return False


def _type_human(driver, el, text):
    ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
    driver.execute_script("arguments[0].focus();", el)
    driver.execute_script(
        "arguments[0].value=''; arguments[0].dispatchEvent(new Event('input',{bubbles:true}));",
        el,
    )
    for ch in text:
        if random.random() < TYPE_ERR:
            wrong = chr(random.randint(97, 122))
            ActionChains(driver).send_keys(wrong).perform()
            time.sleep(random.uniform(TYPE_MIN, TYPE_MAX) / 1000.0)
            ActionChains(driver).send_keys("\b").perform()
            time.sleep(random.uniform(TYPE_MIN, TYPE_MAX) / 1000.0)
        ActionChains(driver).send_keys(ch).perform()
        time.sleep(random.uniform(TYPE_MIN, TYPE_MAX) / 1000.0)
    time.sleep(POST_TYPE_PAUSE / 1000.0)


def _read_cookie_file(cookie_path: Path):
    if not cookie_path.exists():
        return []
    try:
        return json.loads(cookie_path.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_cookies(driver, cookie_path: Path):
    try:
        data = driver.get_cookies()
        cookie_path.parent.mkdir(parents=True, exist_ok=True)
        cookie_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


def ensure_login(
    driver, username: str, password: str, profile_dir: str, timeout: int = 60
) -> bool:
    cookies_file = Path(profile_dir) / "cookies.json"
    cookies = _read_cookie_file(cookies_file)
    driver.get(HOME_URL)
    if cookies:
        for c in cookies:
            ck = {
                k: v
                for k, v in c.items()
                if k
                in {
                    "domain",
                    "expiry",
                    "httpOnly",
                    "name",
                    "path",
                    "sameSite",
                    "secure",
                    "value",
                }
            }
            try:
                driver.add_cookie(ck)
            except Exception:
                continue
        driver.get(HOME_URL)
    _dismiss(driver)
    if _already_logged(driver):
        save_cookies(driver, cookies_file)
        return True

    driver.get(LOGIN_URL)
    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    _dismiss(driver)

    locs_user = [
        (By.CSS_SELECTOR, "input[name='username']"),
        (By.XPATH, "//input[@name='username']"),
        (
            By.XPATH,
            "//input[@aria-label='Telefone, nome de usuário ou email' or @aria-label='Phone number, username, or email']",
        ),
    ]
    locs_pass = [
        (By.CSS_SELECTOR, "input[name='password']"),
        (By.XPATH, "//input[@name='password']"),
        (By.XPATH, "//input[@aria-label='Senha' or @aria-label='Password']"),
    ]

    user_el = None
    pass_el = None
    for by, sel in locs_user:
        try:
            user_el = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((by, sel))
            )
            break
        except Exception:
            pass
    for by, sel in locs_pass:
        try:
            pass_el = WebDriverWait(driver, 8).until(
                EC.presence_of_element_located((by, sel))
            )
            break
        except Exception:
            pass

    if not user_el or not pass_el:
        return False

    _type_human(driver, user_el, username)
    _type_human(driver, pass_el, password)

    try:
        btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        _click(driver, btn)
    except Exception:
        driver.execute_script(
            "document.querySelector(\"button[type='submit']\")?.click();"
        )

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located(
                (
                    By.XPATH,
                    "//nav//a[contains(@href,'/explore/')] | //a[contains(@href,'/accounts/edit')]",
                )
            )
        )
        _dismiss(driver)
        save_cookies(driver, cookies_file)
        return True
    except TimeoutException:
        return False
