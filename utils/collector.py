import os, time, json, random
from pathlib import Path
from typing import Iterable, Set, List
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://www.instagram.com"
TAG_URL = "https://www.instagram.com/explore/tags/{}/"


def _sleep_ms(ms: int):
    time.sleep(ms / 1000.0)


def _human_pause(min_ms: int, max_ms: int, micro_ms: int, micro_prob: float = 0.22):
    t = random.uniform(min_ms, max_ms)
    _sleep_ms(t)
    if random.random() < micro_prob:
        _sleep_ms(micro_ms)


def _maybe_hover(driver, prob: float):
    if random.random() < prob:
        els = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']")
        if els:
            el = random.choice(els)
            try:
                ActionChains(driver).move_to_element(el).pause(
                    random.uniform(0.12, 0.35)
                ).perform()
            except Exception:
                pass


def _scroll_chunk(driver, px: int, jitter_pct: float):
    j = int(px * jitter_pct)
    delta = px + random.randint(-j, j)
    driver.execute_script("window.scrollBy(0, arguments[0]);", max(120, delta))


def _maybe_small_upscroll(driver, prob: float = 0.08):
    if random.random() < prob:
        driver.execute_script(
            "window.scrollBy(0, arguments[0]);", -random.randint(80, 240)
        )


def _visible_links(driver) -> List[str]:
    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']")
    out = []
    for a in anchors:
        try:
            href = a.get_attribute("href") or ""
            if "/p/" in href or "/reel/" in href:
                out.append(href.split("?")[0])
        except Exception:
            continue
    return out


def collect_links_for_tag(
    driver,
    tag: str,
    target_count: int,
    scroll_px_min: int,
    scroll_px_max: int,
    pause_min: int,
    pause_max: int,
    hover_prob: float,
    jitter_pct: float,
    max_steps: int,
    idle_stalls: int,
    micro_pause_ms: int,
    viewport_stop_chance: float,
) -> List[str]:
    url = TAG_URL.format(tag.strip("#").lower())
    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    seen: Set[str] = set()
    stalls = 0
    steps = 0
    while len(seen) < target_count and steps < max_steps and stalls < idle_stalls:
        batch = _visible_links(driver)
        before = len(seen)
        for h in batch:
            seen.add(h)
        gained = len(seen) - before
        stalls = stalls + 1 if gained == 0 else 0
        _maybe_hover(driver, hover_prob)
        if random.random() < viewport_stop_chance:
            _sleep_ms(random.randint(350, 900))
        _scroll_chunk(driver, random.randint(scroll_px_min, scroll_px_max), jitter_pct)
        _maybe_small_upscroll(driver)
        _human_pause(pause_min, pause_max, micro_pause_ms)
        steps += 1
    return list(seen)[:target_count]


def persist_links(out_dir: str, tag: str, links: Iterable[str]):
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    p_txt = Path(out_dir) / f"{tag.strip('#').lower()}.txt"
    p_json = Path(out_dir) / f"{tag.strip('#').lower()}.jsonl"
    existing = set()
    if p_txt.exists():
        existing.update(
            [
                ln.strip()
                for ln in p_txt.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
        )
    new_links = [l for l in links if l not in existing]
    if new_links:
        with p_txt.open("a", encoding="utf-8") as f:
            for l in new_links:
                f.write(l + "\n")
        with p_json.open("a", encoding="utf-8") as f:
            for l in new_links:
                f.write(json.dumps({"tag": tag, "url": l}, ensure_ascii=False) + "\n")


def collect_for_tags(driver, tags: Iterable[str], per_tag: int, out_dir: str):
    pause_min = int(os.getenv("SCROLL_MIN_MS", "400"))
    pause_max = int(os.getenv("SCROLL_MAX_MS", "900"))
    scroll_min = int(os.getenv("SCROLL_PIX_MIN", "450"))
    scroll_max = int(os.getenv("SCROLL_PIX_MAX", "1100"))
    jitter_pct = float(os.getenv("SCROLL_JITTER_PCT", "0.2"))
    max_steps = int(os.getenv("SCROLL_MAX_STEPS", "120"))
    idle_stalls = int(os.getenv("SCROLL_IDLE_STALLS", "20"))
    hover_prob = float(os.getenv("HOVER_PROB", "0.15"))
    micro_pause_ms = int(os.getenv("MICRO_PAUSE_MS", "120"))
    viewport_stop_chance = float(os.getenv("VIEWPORT_STOP_CHANCE", "0.12"))
    for tag in tags:
        links = collect_links_for_tag(
            driver,
            tag,
            per_tag,
            scroll_min,
            scroll_max,
            pause_min,
            pause_max,
            hover_prob,
            jitter_pct,
            max_steps,
            idle_stalls,
            micro_pause_ms,
            viewport_stop_chance,
        )
        persist_links(out_dir, tag, links)
