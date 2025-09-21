# utils/collector.py
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import List, Dict, Iterator, Optional, Set
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from utils.driver import wait_for_page_ready
from utils.logger import get_logger, human_sleep

logger = get_logger("collector")

# ---------- Persistência de "consumidos" por perfil ----------


def _consumed_path(profile_dir: Optional[str]) -> Path:
    base = Path(profile_dir) if profile_dir else Path("sessions/default")
    base.mkdir(parents=True, exist_ok=True)
    return base / "consumed_links.txt"


def _load_consumed(profile_dir: Optional[str]) -> Set[str]:
    p = _consumed_path(profile_dir)
    if not p.exists():
        return set()
    try:
        return {
            line.strip()
            for line in p.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
    except Exception:
        return set()


def mark_target_consumed(profile_dir: Optional[str], target_id: str) -> None:
    try:
        p = _consumed_path(profile_dir)
        with p.open("a", encoding="utf-8") as f:
            f.write(target_id.strip() + "\n")
    except Exception:
        # não bloquear o fluxo se falhar
        pass


# ------------------------------------------------------------


def _mk_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _open_keyword_page(driver: WebDriver, keyword: str) -> None:
    url = (
        f"https://www.instagram.com/explore/search/keyword/?q={quote(keyword.strip())}"
    )
    driver.get(url)
    wait_for_page_ready(driver, timeout=12.0)
    human_sleep((0.8, 1.6), reason=f"abrir keyword '{keyword}'", logger=logger)


def _collect_visible_links(driver: WebDriver, limit: int) -> List[str]:
    urls: List[str] = []
    seen = set()
    cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']")
    for a in cards:
        try:
            href = a.get_attribute("href")
            if href and href not in seen:
                seen.add(href)
                urls.append(href)
                if len(urls) >= limit:
                    break
        except Exception:
            continue
    return urls


def collect_for_tags(
    driver: WebDriver,
    tags: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,  # reservado p/ futuras estratégias
    max_links: int = 20,
    profile_dir: Optional[str] = None,
) -> List[Dict]:
    """
    Visita cada tag (keyword) em /explore/search/keyword/<tag> e extrai links únicos
    de posts/reels, ignorando quaisquer URLs previamente consumidas (persistidas).
    Retorna uma lista de dicts: {"id": <hash>, "url": <url>, "source": "kw:<tag>"}.
    """
    tags = [t for t in (tags or []) if t and t.strip()]
    if not tags:
        logger.warning("Nenhuma tag informada para coleta.")
        return []

    consumed = _load_consumed(profile_dir)
    results: List[Dict] = []

    for tag in tags:
        try:
            _open_keyword_page(driver, tag)
        except Exception as e:
            logger.warning(f"Falha ao abrir keyword '{tag}': {e}")
            continue

        # Pequenos scrolls para carregar mais cartões
        for _ in range(3):
            try:
                driver.execute_script(
                    "window.scrollBy(0, Math.floor(window.innerHeight*0.9));"
                )
            except Exception:
                pass
            human_sleep((0.6, 1.1), reason="scroll leve", logger=logger)

        # Coleta visível
        needed = max_links - len(results)
        if needed <= 0:
            break

        links = _collect_visible_links(driver, limit=needed * 2)  # pega um pouco a mais
        for url in links:
            tid = _mk_id(url)
            if tid in consumed:
                continue
            results.append({"id": tid, "url": url, "source": f"kw:{tag}"})
            if len(results) >= max_links:
                break

        if len(results) >= max_links:
            break

    logger.info(f"Coleta finalizou com {len(results)} links (limite={max_links}).")
    return results


def get_next_target(iterable: Iterator[dict]) -> Optional[dict]:
    try:
        return next(iterable)
    except StopIteration:
        return None
