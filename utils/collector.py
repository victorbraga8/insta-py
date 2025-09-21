# utils/collector.py
from __future__ import annotations

import hashlib
import datetime as _dt
from pathlib import Path
from typing import List, Dict, Iterator, Optional, Set
from urllib.parse import quote

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver

from utils.driver import wait_for_page_ready
from utils.logger import get_logger, human_sleep

logger = get_logger("collector")

# ---------- Persistência de "consumidos" por perfil ----------


def _profile_base(profile_dir: Optional[str]) -> Path:
    base = Path(profile_dir) if profile_dir else Path("sessions/default")
    base.mkdir(parents=True, exist_ok=True)
    return base


def _consumed_path(profile_dir: Optional[str]) -> Path:
    """Arquivo global (compatível com versão anterior)."""
    return _profile_base(profile_dir) / "consumed_links.txt"


def _consumed_daily_path(
    profile_dir: Optional[str], date: Optional[_dt.date] = None
) -> Path:
    """Arquivo diário (evita reutilizar no mesmo dia após reinício)."""
    base = _profile_base(profile_dir) / "consumed"
    base.mkdir(parents=True, exist_ok=True)
    d = date or _dt.date.today()
    return base / f"consumed-{d.isoformat()}.txt"


def _read_lines(p: Path) -> Set[str]:
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


def _load_consumed(profile_dir: Optional[str]) -> Set[str]:
    """Une consumidos globais + consumidos do dia."""
    global_p = _consumed_path(profile_dir)
    daily_p = _consumed_daily_path(profile_dir)
    consumed = _read_lines(global_p) | _read_lines(daily_p)
    logger.info(f"🔒 carregados {len(consumed)} IDs consumidos (global+diário).")
    return consumed


def mark_target_consumed(profile_dir: Optional[str], target_id: str) -> None:
    """Grava o ID no arquivo global e no diário (backward-compatible)."""
    try:
        gid = target_id.strip()
        if not gid:
            return
        with _consumed_path(profile_dir).open("a", encoding="utf-8") as f:
            f.write(gid + "\n")
        with _consumed_daily_path(profile_dir).open("a", encoding="utf-8") as f:
            f.write(gid + "\n")
    except Exception:
        # não bloquear o fluxo se falhar
        pass


# ------------------------------------------------------------


def _mk_id(url: str) -> str:
    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def _open_keyword_page(driver: WebDriver, keyword: str) -> None:
    # Mantém exatamente o recurso indicado por você
    url = (
        f"https://www.instagram.com/explore/search/keyword/?q={quote(keyword.strip())}"
    )
    logger.info(f"🧭 abrindo keyword: {url}")
    driver.get(url)
    wait_for_page_ready(driver, timeout=12.0)
    human_sleep((0.8, 1.6), reason=f"abrir keyword '{keyword}'", logger=logger)


def _collect_visible_links(driver: WebDriver, limit: int) -> List[str]:
    urls: List[str] = []
    seen = set()
    try:
        cards = driver.find_elements(
            By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']"
        )
    except Exception:
        cards = []
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
    Visita cada tag (keyword) em /explore/search/keyword/?q=<tag> e extrai links únicos
    de posts/reels, ignorando quaisquer URLs previamente consumidas (persistidas).
    Retorna uma lista de dicts: {"id": <hash>, "url": <url>, "source": "kw:<tag>"}.
    """
    tags = [t for t in (tags or []) if t and t.strip()]
    if not tags:
        logger.warning("Nenhuma tag informada para coleta.")
        return []

    consumed = _load_consumed(profile_dir)
    results: List[Dict] = []
    seen_ids_exec: Set[str] = set()  # dedupe intra-execução

    for tag in tags:
        try:
            _open_keyword_page(driver, tag)
        except Exception as e:
            logger.warning(f"Falha ao abrir keyword '{tag}': {e}")
            continue

        # Pequenos scrolls para carregar mais cartões (mantido do estável)
        for _ in range(3):
            try:
                driver.execute_script(
                    "window.scrollBy(0, Math.floor(window.innerHeight*0.9));"
                )
            except Exception:
                pass
            human_sleep((0.6, 1.1), reason="scroll leve", logger=logger)

        # Coleta visível inicial
        needed = max_links - len(results)
        if needed <= 0:
            break

        links = _collect_visible_links(driver, limit=needed * 2)  # pega um pouco a mais
        for url in links:
            tid = _mk_id(url)
            if tid in consumed or tid in seen_ids_exec:
                continue
            results.append({"id": tid, "url": url, "source": f"kw:{tag}"})
            seen_ids_exec.add(tid)
            if len(results) >= max_links:
                break

        if len(results) >= max_links:
            break

        # ----- Scroll incremental adicional, se ainda não atingiu o limite -----
        # Mantém comportamento original e apenas amplia quando necessário.
        extra_scrolls = max(3, min(12, max_links // 5))
        sc = 0
        while len(results) < max_links and sc < extra_scrolls:
            sc += 1
            try:
                driver.execute_script(
                    "window.scrollBy(0, Math.floor(window.innerHeight*0.9));"
                )
            except Exception:
                pass
            human_sleep((0.7, 1.4), reason=f"scroll extra ({sc})", logger=logger)

            # Coleta mais cartões após cada scroll extra
            needed = max_links - len(results)
            if needed <= 0:
                break
            more = _collect_visible_links(driver, limit=max(needed * 2, 24))
            added = 0
            for url in more:
                tid = _mk_id(url)
                if tid in consumed or tid in seen_ids_exec:
                    continue
                results.append({"id": tid, "url": url, "source": f"kw:{tag}"})
                seen_ids_exec.add(tid)
                added += 1
                if len(results) >= max_links:
                    break

            logger.info(
                f"[{tag}] scroll extra {sc}: +{added} links (total {len(results)}/{max_links})"
            )

        if len(results) >= max_links:
            break

    logger.info(f"Coleta finalizou com {len(results)} links (limite={max_links}).")
    return results


def get_next_target(iterable: Iterator[dict]) -> Optional[dict]:
    try:
        return next(iterable)
    except StopIteration:
        return None
