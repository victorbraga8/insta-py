# utils/action.py
# Busca por hashtags, escolhe alvos e executa like/comentário.
# Seletores robustos (PT/EN) e tolerantes às variações do DOM do Instagram.

import os
import time
import random
from pathlib import Path
from typing import Dict, List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random, time, os
from pathlib import Path
from typing import Dict, List


# =========================
# TAGS (override por .env)
# =========================
TAGS: List[str] = ["saogoncalo", "niteroi", "riodejaneiro", "saogoncalorj"]
_env_tags = os.getenv("TAGS", "").strip()
if _env_tags:
    parsed = [t.strip().lstrip("#") for t in _env_tags.split(",") if t.strip()]
    if parsed:
        TAGS = parsed


# =========================
# Utils .env
# =========================
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


def _wait_idle():
    time.sleep(max(0, _env_int("WAIT_IDLE_MS", 1200)) / 1000.0)


def _safe_scroll(driver: WebDriver):
    lo = _env_int("SCROLL_MIN_PX", 350)
    hi = _env_int("SCROLL_MAX_PX", 900)
    jitter = float(os.getenv("SCROLL_JITTER_PCT", "0.3"))
    base = random.uniform(lo, max(lo, hi))
    delta = base + base * random.uniform(-abs(jitter), abs(jitter))
    driver.execute_script(f"window.scrollBy(0, {int(delta)});")


# =========================
# Estado por perfil
# =========================
_state: Dict[str, Dict] = {}


def _state_for(profile_id: str) -> Dict:
    if profile_id not in _state:
        tags = TAGS.copy()
        if _env_bool("TAGS_SHUFFLE", True):
            random.shuffle(tags)
        _state[profile_id] = {
            "tags": tags,
            "tag_idx": 0,
            "actions_by_tag": {t: 0 for t in tags},
            "last_grid_urls": set(),
        }
    return _state[profile_id]


def _rotate_tag_if_needed(profile_id: str):
    st = _state_for(profile_id)
    per_tag_limit = _env_int("PER_TAG_MAX_ACTIONS", 12)
    tag = st["tags"][st["tag_idx"]]
    if st["actions_by_tag"].get(tag, 0) >= per_tag_limit:
        st["tag_idx"] = (st["tag_idx"] + 1) % len(st["tags"])
        st["last_grid_urls"].clear()


def _bump_action_count(profile_id: str):
    st = _state_for(profile_id)
    tag = st["tags"][st["tag_idx"]]
    st["actions_by_tag"][tag] = st["actions_by_tag"].get(tag, 0) + 1


# =========================
# Navegação / coleta
# =========================
def _open_tag_grid(driver: WebDriver, tag: str):
    url = f"https://www.instagram.com/explore/tags/{tag}/"
    if url.rstrip("/") not in driver.current_url.rstrip("/"):
        driver.get(url)
    _wait_idle()


def _collect_grid_links(driver: WebDriver) -> List[str]:
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']")
    urls, seen = [], set()
    for a in anchors:
        try:
            href = (a.get_attribute("href") or "").split("?")[0]
            if (
                "instagram.com" in href
                and ("/p/" in href or "/reel/" in href)
                and href not in seen
            ):
                urls.append(href)
                seen.add(href)
        except Exception:
            continue
    return urls


def _post_id_from_url(url: str) -> Optional[str]:
    try:
        parts = url.split("/")
        for i, p in enumerate(parts):
            if p in ("p", "reel") and i + 1 < len(parts):
                return parts[i + 1]
    except Exception:
        pass
    return None


def get_next_target(
    driver: WebDriver, profile_id: str, seen_ids: set
) -> Optional[Dict]:
    st = _state_for(profile_id)
    _rotate_tag_if_needed(profile_id)
    tag = st["tags"][st["tag_idx"]]
    _open_tag_grid(driver, tag)

    tries = 0
    while tries < 6:
        urls = _collect_grid_links(driver)
        new_urls = [u for u in urls if u not in st["last_grid_urls"]]
        st["last_grid_urls"] = set(urls)

        for u in new_urls or urls:
            pid = _post_id_from_url(u)
            if pid and pid not in seen_ids:
                return {"id": pid, "url": u}

        _safe_scroll(driver)
        _wait_idle()
        tries += 1

    st["tag_idx"] = (st["tag_idx"] + 1) % len(st["tags"])
    st["last_grid_urls"].clear()
    _open_tag_grid(driver, st["tags"][st["tag_idx"]])
    urls = _collect_grid_links(driver)
    for u in urls:
        pid = _post_id_from_url(u)
        if pid and pid not in seen_ids:
            return {"id": pid, "url": u}
    return None


# =========================
# Helpers de click
# =========================
def _open_post(driver: WebDriver, url: str) -> bool:
    try:
        driver.get(url)
        _wait_idle()
        WebDriverWait(driver, _env_int("NAVIGATION_TIMEOUT_MS", 35000) // 1000).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "article"))
        )
        return True
    except Exception:
        return False


def _closest_clickable_for_svg(driver: WebDriver, svg_el):
    # 1) button ancestral
    try:
        btn = svg_el.find_element(By.XPATH, "./ancestor::button[1]")
        return btn
    except Exception:
        pass
    # 2) ancestral com role=button
    try:
        role_btn = svg_el.find_element(By.XPATH, "./ancestor::*[@role='button'][1]")
        return role_btn
    except Exception:
        pass
    # 3) o próprio svg
    return svg_el


def _js_click(driver: WebDriver, el):
    driver.execute_script("arguments[0].click();", el)


# =========================
# Ações
# =========================
def do_like(driver: WebDriver, target: Dict) -> bool:
    """
    CLICA exatamente no SVG:
      svg[aria-label="Curtir"][height="24"][width="24"]
    Se já tiver 'Descurtir', considera sucesso (idempotente).
    """
    url = target.get("url")
    if not url or not _open_post(driver, url):
        return False

    # já curtido?
    if driver.find_elements(
        By.CSS_SELECTOR, 'svg[aria-label="Descurtir"], svg[aria-label="Unlike"]'
    ):
        return True

    # seletor EXATO pedido
    like_css = 'svg[aria-label="Curtir"][height="24"][width="24"]'
    svgs = driver.find_elements(By.CSS_SELECTOR, like_css)
    if not svgs:
        return False

    svg = svgs[0]

    # scroll + clique direto no SVG (sem ancestral)
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'});", svg
        )
        time.sleep(0.12)
        # clique real; se der overlay, força via JS
        try:
            WebDriverWait(driver, 3).until(EC.element_to_be_clickable(svg)).click()
        except Exception:
            driver.execute_script("arguments[0].click();", svg)
        time.sleep(random.uniform(0.25, 0.5))
    except Exception:
        return False

    # confirmador: virou 'Descurtir'?
    if driver.find_elements(
        By.CSS_SELECTOR, 'svg[aria-label="Descurtir"], svg[aria-label="Unlike"]'
    ):
        _bump_action_count(_infer_profile())
        return True

    return False


def _read_comments_from_file(path: str, min_chars: int) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    out = []
    with p.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            c = (line or "").strip()
            if len(c) >= max(0, min_chars):
                out.append(c)
    return out


def _human_type(el, text: str, min_ms: int, max_ms: int):
    lo = max(0, min_ms)
    hi = max(lo, max_ms)
    for ch in text:
        el.send_keys(ch)
        time.sleep(random.uniform(lo, hi) / 1000.0)


def do_comment(
    driver: WebDriver,
    target: Dict,
    comments_file: str,
    type_min_ms: int,
    type_max_ms: int,
    min_chars: int,
) -> bool:
    """
    Abre o post e CLICA exatamente no textarea:
      textarea[aria-label="Adicione um comentário..."][placeholder="Adicione um comentário..."]
    Depois digita com latência humana e envia com ENTER.
    """
    url = target.get("url")
    if not url or not _open_post(driver, url):
        return False

    comments = _read_comments_from_file(comments_file, min_chars)
    if not comments:
        return False
    text = random.choice(comments)

    # seletor EXATO que você forneceu
    ta_css = 'textarea[aria-label="Adicione um comentário..."][placeholder="Adicione um comentário..."]'

    # se não estiver presente ainda, tente revelar (alguns layouts mostram após um clique no ícone de comentar)
    box = None
    try:
        box = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ta_css))
        )
    except Exception:
        # tenta clicar no ícone de comentar 24x24 e procurar de novo
        try:
            icon = driver.find_elements(
                By.CSS_SELECTOR, 'svg[aria-label="Comentar"][height="24"][width="24"]'
            )
            if icon:
                driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center'});", icon[0]
                )
                try:
                    WebDriverWait(driver, 2).until(
                        EC.element_to_be_clickable(icon[0])
                    ).click()
                except Exception:
                    driver.execute_script("arguments[0].click();", icon[0])
                time.sleep(0.2)
        except Exception:
            pass
        try:
            box = WebDriverWait(driver, 4).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ta_css))
            )
        except Exception:
            return False

    # clique REAL no textarea + foco explícito
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center', inline:'center'});", box
        )
        time.sleep(0.1)
        try:
            WebDriverWait(driver, 2).until(EC.element_to_be_clickable(box)).click()
        except Exception:
            driver.execute_script("arguments[0].click();", box)
        driver.execute_script("arguments[0].focus();", box)
        time.sleep(random.uniform(0.12, 0.25))
        _human_type(box, text, type_min_ms, type_max_ms)
        time.sleep(random.uniform(0.08, 0.16))
        box.send_keys(Keys.ENTER)
    except Exception:
        return False

    _bump_action_count(_infer_profile())
    return True


# =========================
# Aux
# =========================
def _infer_profile() -> str:
    profiles = [
        p.strip() for p in os.getenv("PROFILES", "perfil1").split(",") if p.strip()
    ]
    return profiles[0] if profiles else "perfil1"
