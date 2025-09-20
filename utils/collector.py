import os, time, json, random
from pathlib import Path
from typing import Iterable, Set, List
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TAG_URL = "https://www.instagram.com/explore/tags/{}/"


def _ms(n):
    time.sleep(n / 1000.0)


def _human_pause(min_ms, max_ms, micro_ms, micro_prob=0.25):
    _ms(random.uniform(min_ms, max_ms))
    if random.random() < micro_prob:
        _ms(micro_ms)


def _maybe_hover(driver, prob):
    if random.random() < prob:
        els = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']")
        if els:
            el = random.choice(els)
            try:
                ActionChains(driver).move_to_element(el).pause(
                    random.uniform(0.15, 0.4)
                ).perform()
            except Exception:
                pass


def _scroll_chunk(driver, px, jitter_pct):
    j = int(px * jitter_pct)
    delta = px + random.randint(-j, j)
    driver.execute_script("window.scrollBy(0, arguments[0]);", max(120, delta))


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
    tag,
    target_count,
    scroll_px_min,
    scroll_px_max,
    pause_min,
    pause_max,
    hover_prob,
    jitter_pct,
    max_steps,
    idle_stalls,
    micro_pause_ms,
    viewport_stop_chance,
    settle_min,
    settle_max,
):
    url = TAG_URL.format(tag.strip("#").lower())
    driver.get(url)
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    _ms(random.uniform(settle_min, settle_max))
    seen: Set[str] = set()
    stalls = 0
    steps = 0
    while len(seen) < target_count and steps < max_steps and stalls < idle_stalls:
        batch = _visible_links(driver)
        before = len(seen)
        for h in batch:
            seen.add(h)
        stalls = stalls + 1 if len(seen) == before else 0
        _maybe_hover(driver, hover_prob)
        if random.random() < viewport_stop_chance:
            _ms(random.randint(350, 900))
        _scroll_chunk(driver, random.randint(scroll_px_min, scroll_px_max), jitter_pct)
        _human_pause(pause_min, pause_max, micro_pause_ms)
        steps += 1
    return list(seen)[:target_count]


def persist_links(out_dir, tag, links):
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
    pause_min = int(os.getenv("SCROLL_MIN_MS", "650"))
    pause_max = int(os.getenv("SCROLL_MAX_MS", "1300"))
    scroll_min = int(os.getenv("SCROLL_PIX_MIN", "450"))
    scroll_max = int(os.getenv("SCROLL_PIX_MAX", "1100"))
    jitter_pct = float(os.getenv("SCROLL_JITTER_PCT", "0.2"))
    max_steps = int(os.getenv("SCROLL_MAX_STEPS", "140"))
    idle_stalls = int(os.getenv("SCROLL_IDLE_STALLS", "22"))
    hover_prob = float(os.getenv("HOVER_PROB", "0.15"))
    micro_pause_ms = int(os.getenv("MICRO_PAUSE_MS", "180"))
    viewport_stop_chance = float(os.getenv("VIEWPORT_STOP_CHANCE", "0.18"))
    settle_min = int(os.getenv("SETTLE_MIN_MS", "800"))
    settle_max = int(os.getenv("SETTLE_MAX_MS", "1400"))
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
            settle_min,
            settle_max,
        )
        persist_links(out_dir, tag, links)
