import os, time, json, random
from pathlib import Path
from typing import Dict, List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _sleep_ms(ms: int):
    time.sleep(ms / 1000.0)


def _wait_click(driver, css: str, t: int = 8):
    el = WebDriverWait(driver, t).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, css))
    )
    el.click()
    return el


def _visible(driver, css: str, t: int = 8):
    return WebDriverWait(driver, t).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, css))
    )


def _type_human(driver, el, text: str, lo: int, hi: int, err: float, post_pause: int):
    ActionChains(driver).move_to_element(el).pause(0.1).click().perform()
    driver.execute_script("arguments[0].focus();", el)
    driver.execute_script("arguments[0].value='';", el)
    for ch in text:
        if random.random() < err:
            wrong = chr(random.randint(97, 122))
            ActionChains(driver).send_keys(wrong).perform()
            _sleep_ms(random.randint(lo, hi))
            ActionChains(driver).send_keys("\b").perform()
            _sleep_ms(random.randint(lo, hi))
        ActionChains(driver).send_keys(ch).perform()
        _sleep_ms(random.randint(lo, hi))
    _sleep_ms(post_pause)


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


def like_post(driver) -> bool:
    try:
        btn_unlike = driver.find_elements(
            By.CSS_SELECTOR, "svg[aria-label='Descurtir'], svg[aria-label='Unlike']"
        )
        if btn_unlike:
            return True
        btn_like = driver.find_elements(
            By.CSS_SELECTOR, "svg[aria-label='Curtir'], svg[aria-label='Like']"
        )
        if not btn_like:
            return False
        btn_like[0].find_element(By.XPATH, "./ancestor::button").click()
        _sleep_ms(random.randint(250, 700))
        return True
    except Exception:
        return False


def open_comment_box(driver):
    try:
        cbtn = driver.find_elements(
            By.CSS_SELECTOR, "svg[aria-label='Comentar'], svg[aria-label='Comment']"
        )
        if cbtn:
            cbtn[0].find_element(By.XPATH, "./ancestor::button").click()
            _sleep_ms(random.randint(200, 500))
    except Exception:
        pass


def comment_post(
    driver, text: str, lo: int, hi: int, err: float, post_pause: int
) -> bool:
    try:
        open_comment_box(driver)
        box = None
        for sel in [
            "form textarea",
            "form[method='POST'] textarea",
            "textarea[aria-label]",
        ]:
            els = driver.find_elements(By.CSS_SELECTOR, sel)
            if els:
                box = els[0]
                break
        if not box:
            return False
        _type_human(driver, box, text, lo, hi, err, post_pause)
        submit = driver.find_elements(
            By.XPATH, "//form//button[@type='submit' or .='Post' or .='Publicar']"
        )
        if submit:
            submit[0].click()
        else:
            ActionChains(driver).key_down("\n").key_up("\n").perform()
        _sleep_ms(random.randint(650, 1200))
        return True
    except Exception:
        return False


def view_reel(driver, min_ms: int, max_ms: int) -> bool:
    try:
        _sleep_ms(random.randint(min_ms, max_ms))
        return True
    except Exception:
        return False
