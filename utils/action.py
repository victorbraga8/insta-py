# utils/action.py
from __future__ import annotations

import time
import random
from typing import Optional, Dict, Iterable, List, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException, TimeoutException

from utils.logger import get_logger
from utils.driver import wait_for_page_ready
from utils.collector import mark_target_consumed

logger = get_logger("action")


# =========================
# Utilitários
# =========================
def _sleep(a: float, b: float) -> None:
    t = random.uniform(a, b)
    logger.info(f"⏱️ aguardando {t:.3f}s")
    time.sleep(t)


def _human_type(
    el, text: str, min_delay: float = 0.03, max_delay: float = 0.12
) -> None:
    for ch in text:
        el.send_keys(ch)
        time.sleep(random.uniform(min_delay, max_delay))


def _js_query(driver: WebDriver, css: str):
    try:
        return driver.execute_script(
            "return document.querySelector(arguments[0]);", css
        )
    except Exception:
        return None


def _js_query_all(driver: WebDriver, css: str) -> list:
    try:
        return (
            driver.execute_script(
                "return Array.from(document.querySelectorAll(arguments[0]));", css
            )
            or []
        )
    except Exception:
        return []


def _xpath_all(driver: WebDriver, xpath: str) -> list:
    try:
        return driver.find_elements(By.XPATH, xpath) or []
    except Exception:
        return []


def _highlight(driver: WebDriver, el, color: str = "red") -> None:
    try:
        driver.execute_script(
            """
            const el = arguments[0], c = arguments[1];
            el.scrollIntoView({block:'center', inline:'center'});
            el.style.outline = `3px solid ${c}`;
            el.style.outlineOffset = '2px';
            """,
            el,
            color,
        )
    except Exception:
        pass


def _describe_el(driver: WebDriver, el) -> str:
    try:
        return driver.execute_script(
            """
            const el = arguments[0];
            const r = el.getBoundingClientRect();
            const a = el.getAttribute('aria-label');
            const w = el.getAttribute('width');
            const h = el.getAttribute('height');
            return `${el.tagName.toLowerCase()} aria='${a}' w=${w||'-'} h=${h||'-'} bx=${r.left.toFixed(0)},${r.top.toFixed(0)},${r.width.toFixed(0)}x${r.height.toFixed(0)}`;
            """,
            el,
        )
    except Exception:
        return "<element>"


def _navigate_to_target(driver: WebDriver, target: Dict) -> bool:
    url = target.get("url")
    if not url:
        return False
    logger.info(f"🧭 navegando para: {url}")
    try:
        driver.get(url)
    except WebDriverException:
        try:
            driver.get(url)
        except Exception as e:
            logger.warning(f"Falha ao navegar para {url}: {e}")
            return False
    wait_for_page_ready(driver, timeout=12.0)
    _sleep(0.4, 0.9)
    return True


# =========================
# Seletores
# =========================
LIKE_CSS_PT = 'svg[aria-label="Curtir"][width="24"][height="24"]'
LIKE_CSS_EN = 'svg[aria-label="Like"][width="24"][height="24"]'
UNLIKE_CSS_PT = 'svg[aria-label="Descurtir"][width="24"][height="24"]'
UNLIKE_CSS_EN = 'svg[aria-label="Unlike"][width="24"][height="24"]'

# XPath com local-name(), como no fórum — com width/height 24
LIKE_XP_PT = (
    "//*[local-name()='svg' and @aria-label='Curtir' and @width='24' and @height='24']"
)
LIKE_XP_EN = (
    "//*[local-name()='svg' and @aria-label='Like' and @width='24' and @height='24']"
)
UNLIKE_XP_PT = "//*[local-name()='svg' and @aria-label='Descurtir' and @width='24' and @height='24']"
UNLIKE_XP_EN = (
    "//*[local-name()='svg' and @aria-label='Unlike' and @width='24' and @height='24']"
)

# Último recurso de debug: qualquer svg 24x24 (não usamos para clicar, apenas logging)
ANY_24 = "//*[local-name()='svg' and @width='24' and @height='24']"

COMMENT_TA_EXACT = 'textarea[aria-label="Adicione um comentário..."]'
COMMENT_TA_UNICODE = (
    'textarea[aria-label="Adicione um comentário…"]'  # reticência unicode
)


# =========================
# Coleta / verificação Like
# =========================
def _inventory_svgs(driver: WebDriver) -> Dict[str, List]:
    """Varre múltiplos seletores e retorna um inventário para logging e tentativa."""
    inv: Dict[str, List] = {
        LIKE_CSS_PT: _js_query_all(driver, LIKE_CSS_PT),
        LIKE_CSS_EN: _js_query_all(driver, LIKE_CSS_EN),
        LIKE_XP_PT: _xpath_all(driver, LIKE_XP_PT),
        LIKE_XP_EN: _xpath_all(driver, LIKE_XP_EN),
        UNLIKE_CSS_PT: _js_query_all(driver, UNLIKE_CSS_PT),
        UNLIKE_CSS_EN: _js_query_all(driver, UNLIKE_CSS_EN),
        UNLIKE_XP_PT: _xpath_all(driver, UNLIKE_XP_PT),
        UNLIKE_XP_EN: _xpath_all(driver, UNLIKE_XP_EN),
        ANY_24: _xpath_all(driver, ANY_24),  # debug view
    }
    # Log do inventário
    logger.info("🔬 inventário de SVGs 24x24 relevantes:")
    for sel, items in inv.items():
        if sel is ANY_24:
            logger.info(f"  {sel} => {len(items)} elementos (apenas debug)")
        else:
            logger.info(f"  {sel} => {len(items)} elementos")
        # listar primeiros 5 para não poluir
        for el in items[:5]:
            logger.info(f"    • {_describe_el(driver, el)}")
    return inv


def _already_liked(driver: WebDriver) -> bool:
    # qualquer uma das variantes de 'descurtir'
    for sel in (UNLIKE_CSS_PT, UNLIKE_CSS_EN):
        el = _js_query(driver, sel)
        if el:
            logger.info(
                f"✅ detectado estado curtido via CSS: {_describe_el(driver, el)}"
            )
            return True
    for xp in (UNLIKE_XP_PT, UNLIKE_XP_EN):
        els = _xpath_all(driver, xp)
        if els:
            logger.info(
                f"✅ detectado estado curtido via XPath: {_describe_el(driver, els[0])}"
            )
            return True
    return False


def _gather_like_candidates(driver: WebDriver) -> List[Tuple[str, object]]:
    """Retorna lista ordenada (seletor, elemento) de candidatos a 'Curtir' (SVG 24x24)."""
    inv = _inventory_svgs(driver)

    ordered_keys = [
        LIKE_CSS_PT,
        LIKE_CSS_EN,
        LIKE_XP_PT,
        LIKE_XP_EN,
    ]
    seen_ids = set()
    candidates: List[Tuple[str, object]] = []
    for key in ordered_keys:
        for el in inv.get(key, []):
            # deduplicar pelo id interno do WebElement
            try:
                el_id = getattr(el, "id", None)
            except Exception:
                el_id = None
            if el_id in seen_ids:
                continue
            seen_ids.add(el_id)
            candidates.append((key, el))

    logger.info(f"🎯 candidatos 'Curtir' (em ordem): {len(candidates)}")
    for i, (sel, el) in enumerate(candidates[:6], 1):
        logger.info(f"  [{i}] {sel} -> {_describe_el(driver, el)}")
    return candidates


def _click_svg_like(driver: WebDriver, el) -> bool:
    # 1) clicar no SVG
    try:
        _highlight(driver, el, "red")
        logger.info(f"🖱️ click SVG alvo: {_describe_el(driver, el)}")
        driver.execute_script("arguments[0].click();", el)
        return True
    except Exception as e:
        logger.warning(f"Falha ao clicar no SVG (direto): {e}")

    # 2) clicar no pai
    try:
        parent = driver.execute_script("return arguments[0].parentElement;", el)
        if parent:
            _highlight(driver, parent, "red")
            logger.info(f"🖱️ fallback click PAI: {_describe_el(driver, parent)}")
            driver.execute_script("arguments[0].click();", parent)
            return True
    except Exception as e:
        logger.warning(f"Falha ao clicar no pai: {e}")

    # 3) clicar no avô (padrão do snippet do fórum: /../..)
    try:
        grand = driver.execute_script(
            "return arguments[0].parentElement?.parentElement;", el
        )
        if grand:
            _highlight(driver, grand, "red")
            logger.info(f"🖱️ fallback click AVÔ: {_describe_el(driver, grand)}")
            driver.execute_script("arguments[0].click();", grand)
            return True
    except Exception as e:
        logger.warning(f"Falha ao clicar no avô: {e}")

    return False


# =========================
# Ações públicas
# =========================
def do_like(
    driver: WebDriver, target: Dict, *, profile_dir: Optional[str] = None
) -> bool:
    if not _navigate_to_target(driver, target):
        return False

    if _already_liked(driver):
        logger.info("Post já curtido — marcando como consumido e pulando.")
        mark_target_consumed(profile_dir, target.get("id", target.get("url", "")))
        return True

    candidates = _gather_like_candidates(driver)
    if not candidates:
        logger.info("❌ nenhum candidato de like encontrado (SVG 24x24).")
        return False

    # tenta cada candidato até um clique bem-sucedido
    for sel, el in candidates:
        logger.info(f"tentando clicar candidato '{sel}' -> {_describe_el(driver, el)}")
        ok = _click_svg_like(driver, el)
        logger.info(f"resultado do clique: {'SUCESSO' if ok else 'FALHA'}")
        if not ok:
            continue

        # confirmar transição para 'Descurtir'
        end = time.time() + 3.5
        while time.time() < end:
            if _already_liked(driver):
                logger.info("👍 estado mudou para 'Descurtir' — like confirmado.")
                mark_target_consumed(
                    profile_dir, target.get("id", target.get("url", ""))
                )
                return True
            time.sleep(0.15)
        logger.info(
            "⚠️ clique executado, mas não confirmou 'Descurtir' — tentando próximo candidato…"
        )

    logger.info("❌ esgotou candidatos de like sem confirmação.")
    return False


def do_comment(
    driver: WebDriver, target: Dict, text: str, *, profile_dir: Optional[str] = None
) -> bool:
    if not text or not text.strip():
        logger.info("❌ comentário vazio — pulando.")
        return False

    if not _navigate_to_target(driver, target):
        return False

    logger.info(f"🔎 procurando textarea exato: {COMMENT_TA_EXACT}")
    textarea = _js_query(driver, COMMENT_TA_EXACT)
    if not textarea:
        logger.info(f"   não achou; tentando variação unicode: {COMMENT_TA_UNICODE}")
        textarea = _js_query(driver, COMMENT_TA_UNICODE)

    if not textarea:
        logger.info("❌ textarea de comentário não encontrada.")
        return False

    try:
        _highlight(driver, textarea, "red")
        textarea.click()
    except Exception:
        pass
    _sleep(0.12, 0.30)

    txt = text.strip()
    logger.info(f"⌨️ digitando comentário ({len(txt)} chars)")
    _human_type(textarea, txt, min_delay=0.02, max_delay=0.08)
    _sleep(0.20, 0.45)

    try:
        textarea.send_keys(Keys.ENTER)
        logger.info("↩️ ENTER enviado")
    except Exception as e:
        logger.warning(f"Falha ao enviar ENTER: {e}")

    _sleep(0.6, 1.1)

    try:
        val = textarea.get_attribute("value") or ""
        logger.info(f"   pós-ENTER, textarea length={len(val)}")
        if val.strip() == "":
            mark_target_consumed(profile_dir, target.get("id", target.get("url", "")))
            logger.info("✅ comentário aparentemente publicado (textarea vazia).")
            return True
    except Exception:
        pass

    # busca por fragmento
    frag = txt[:20]
    try:
        found = driver.find_elements(By.XPATH, f"//*[contains(text(), {repr(frag)})]")
        logger.info(f"   busca por fragmento {frag!r} -> {len(found)} nós")
        if found:
            mark_target_consumed(profile_dir, target.get("id", target.get("url", "")))
            return True
    except Exception:
        pass

    logger.info("⚠️ não foi possível confirmar publicação do comentário.")
    return False
