import os, time, json, random
from pathlib import Path
from typing import List
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _ms(n):
    time.sleep(n / 1000.0)


NAV_MIN = int(os.getenv("NAVIGATE_MIN_MS", "700"))
NAV_MAX = int(os.getenv("NAVIGATE_MAX_MS", "1500"))
ACT_MIN = int(os.getenv("ACTION_AFTER_MIN_MS", "800"))
ACT_MAX = int(os.getenv("ACTION_AFTER_MAX_MS", "1600"))


def mark_comment_used(recent_path: str, text: str, recent_limit: int):
    rp = Path(recent_path)
    lines = []
    if rp.exists():
        lines = [
            ln.strip()
            for ln in rp.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    lines.append(text)
    lines = lines[-recent_limit:]
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(lines), encoding="utf-8")


def _hover_el(driver, el, lo=120, hi=320):
    try:
        ActionChains(driver).move_to_element(el).pause(
            random.uniform(lo / 1000, hi / 1000)
        ).perform()
    except Exception:
        pass


def _type_human(driver, el, text: str, lo: int, hi: int, err: float, post_pause: int):
    ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
    driver.execute_script("arguments[0].focus();", el)
    driver.execute_script("arguments[0].value='';", el)
    for ch in text:
        if random.random() < err:
            wrong = chr(random.randint(97, 122))
            ActionChains(driver).send_keys(wrong).perform()
            _ms(random.randint(lo, hi))
            ActionChains(driver).send_keys("\b").perform()
            _ms(random.randint(lo, hi))
        ActionChains(driver).send_keys(ch).perform()
        _ms(random.randint(lo, hi))
    _ms(post_pause)


def _find_like_button(driver):
    try:
        svg = WebDriverWait(driver, 6).until(
            EC.presence_of_element_located(
                (By.XPATH, "//svg[@aria-label='Curtir' or @aria-label='Like']")
            )
        )
        try:
            btn = svg.find_element(By.XPATH, "./ancestor::button[1]")
            return btn
        except Exception:
            pass
        try:
            rolebtn = svg.find_element(By.XPATH, "./ancestor::*[@role='button'][1]")
            return rolebtn
        except Exception:
            return None
    except Exception:
        return None


def _is_liked(driver):
    try:
        liked = driver.find_elements(
            By.XPATH, "//svg[@aria-label='Descurtir' or @aria-label='Unlike']"
        )
        return len(liked) > 0
    except Exception:
        return False


def like_post(driver) -> bool:
    try:
        if _is_liked(driver):
            return True
        btn = _find_like_button(driver)
        if not btn:
            return False
        _hover_el(driver, btn)
        btn.click()
        _ms(random.randint(240, 680))
        return True
    except Exception:
        return False


def open_comment_box(driver):
    try:
        cbtns = driver.find_elements(
            By.XPATH,
            "//svg[@aria-label='Comentar' or @aria-label='Comment']/ancestor::button[1]",
        )
        if cbtns:
            _hover_el(driver, cbtns[0])
            cbtns[0].click()
            _ms(random.randint(200, 500))
    except Exception:
        pass


def _find_textarea(driver):
    sels = [
        (
            By.XPATH,
            "//textarea[@aria-label='Adicione um comentário...' or contains(@aria-label,'coment') or contains(@aria-label,'comment')]",
        ),
        (
            By.XPATH,
            "//textarea[@placeholder='Adicione um comentário...' or contains(@placeholder,'coment') or contains(@placeholder,'comment')]",
        ),
        (By.CSS_SELECTOR, "form textarea"),
    ]
    for by, sel in sels:
        els = driver.find_elements(by, sel)
        if els:
            return els[0]
    return None


def comment_post(
    driver, text: str, lo: int, hi: int, err: float, post_pause: int
) -> bool:
    try:
        open_comment_box(driver)
        box = _find_textarea(driver)
        if not box:
            return False
        _hover_el(driver, box)
        _type_human(driver, box, text, lo, hi, err, post_pause)
        submit = driver.find_elements(
            By.XPATH, "//form//button[@type='submit' or .='Post' or .='Publicar']"
        )
        if submit:
            _hover_el(driver, submit[0])
            submit[0].click()
        else:
            ActionChains(driver).key_down("\n").key_up("\n").perform()
        _ms(random.randint(650, 1200))
        return True
    except Exception:
        return False


def view_reel(driver, min_ms: int, max_ms: int) -> bool:
    try:
        _ms(random.randint(min_ms, max_ms))
        return True
    except Exception:
        return False


def load_comments_pool(path: str, recent_path: str, recent_limit: int) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    pool = [
        ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    rp = Path(recent_path)
    recent = []
    if rp.exists():
        recent = [
            ln.strip()
            for ln in rp.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    cand = [c for c in pool if c not in set(recent)]
    random.shuffle(cand)
    if not cand:
        cand = pool[:]
    random.shuffle(cand)
    return cand
