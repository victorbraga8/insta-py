# utils/action.py
from __future__ import annotations

import os
import time
import random
from typing import Optional, Dict, List, Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

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


def _xpath_one(driver: WebDriver, xpath: str):
    try:
        els = driver.find_elements(By.XPATH, xpath)
        return els[0] if els else None
    except Exception:
        return None


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
# Seletores Like (PT/EN)
# =========================
LIKE_CSS_PT = 'svg[aria-label="Curtir"][width="24"][height="24"]'
LIKE_CSS_EN = 'svg[aria-label="Like"][width="24"][height="24"]'
UNLIKE_CSS_PT = 'svg[aria-label="Descurtir"][width="24"][height="24"]'
UNLIKE_CSS_EN = 'svg[aria-label="Unlike"][width="24"][height="24"]'

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

ANY_24 = "//*[local-name()='svg' and @width='24' and @height='24']"  # debug


# =========================
# Comentário – PT/EN e … / ...
# =========================
TA_PT_ELLIPSIS = 'textarea[aria-label="Adicione um comentário…"]'
TA_PT_THREEDOTS = 'textarea[aria-label="Adicione um comentário..."]'
TA_EN_ELLIPSIS = 'textarea[aria-label="Add a comment…"]'
TA_EN_THREEDOTS = 'textarea[aria-label="Add a comment..."]'

# Botão de publicar (UI nova usa uma <div role="button"> com o texto)
POST_BTN_XP_EN = "//div[@role='button' and normalize-space()='Post']"
POST_BTN_XP_PT = "//div[@role='button' and normalize-space()='Publicar']"
POST_BTN_XP_EN_SPAN = "//div[@role='button'][.//span[normalize-space()='Post']]"
POST_BTN_XP_PT_SPAN = "//div[@role='button'][.//span[normalize-space()='Publicar']]"


# =========================
# Like helpers
# =========================
def _inventory_svgs(driver: WebDriver) -> Dict[str, List]:
    inv: Dict[str, List] = {
        LIKE_CSS_PT: _js_query_all(driver, LIKE_CSS_PT),
        LIKE_CSS_EN: _js_query_all(driver, LIKE_CSS_EN),
        LIKE_XP_PT: _xpath_all(driver, LIKE_XP_PT),
        LIKE_XP_EN: _xpath_all(driver, LIKE_XP_EN),
        UNLIKE_CSS_PT: _js_query_all(driver, UNLIKE_CSS_PT),
        UNLIKE_CSS_EN: _js_query_all(driver, UNLIKE_CSS_EN),
        UNLIKE_XP_PT: _xpath_all(driver, UNLIKE_XP_PT),
        UNLIKE_XP_EN: _xpath_all(driver, UNLIKE_XP_EN),
        ANY_24: _xpath_all(driver, ANY_24),
    }
    logger.info("🔬 inventário de SVGs 24x24 relevantes:")
    for sel, items in inv.items():
        tag = " (apenas debug)" if sel is ANY_24 else ""
        logger.info(f"  {sel} => {len(items)} elementos{tag}")
        for el in items[:5]:
            logger.info(f"    • {_describe_el(driver, el)}")
    return inv


def _already_liked(driver: WebDriver) -> bool:
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
    inv = _inventory_svgs(driver)
    ordered_keys = [LIKE_CSS_PT, LIKE_CSS_EN, LIKE_XP_PT, LIKE_XP_EN]
    seen_ids = set()
    candidates: List[Tuple[str, object]] = []
    for key in ordered_keys:
        for el in inv.get(key, []):
            el_id = getattr(el, "id", None)
            if el_id in seen_ids:
                continue
            seen_ids.add(el_id)
            candidates.append((key, el))
    logger.info(f"🎯 candidatos 'Curtir' (em ordem): {len(candidates)}")
    for i, (sel, el) in enumerate(candidates[:6], 1):
        logger.info(f"  [{i}] {sel} -> {_describe_el(driver, el)}")
    return candidates


def _click_svg_like(driver: WebDriver, el) -> bool:
    try:
        # micro-delays humanos
        _sleep(0.10, 0.25)
        _highlight(driver, el, "red")
        logger.info(f"🖱️ click SVG alvo: {_describe_el(driver, el)}")
        driver.execute_script("arguments[0].click();", el)
        _sleep(0.10, 0.25)
        return True
    except Exception as e:
        logger.warning(f"Falha ao clicar no SVG (direto): {e}")
    try:
        parent = driver.execute_script("return arguments[0].parentElement;", el)
        if parent:
            _sleep(0.08, 0.18)
            _highlight(driver, parent, "red")
            logger.info(f"🖱️ fallback click PAI: {_describe_el(driver, parent)}")
            driver.execute_script("arguments[0].click();", parent)
            _sleep(0.10, 0.25)
            return True
    except Exception as e:
        logger.warning(f"Falha ao clicar no pai: {e}")
    try:
        grand = driver.execute_script(
            "return arguments[0].parentElement?.parentElement;", el
        )
        if grand:
            _sleep(0.08, 0.18)
            _highlight(driver, grand, "red")
            logger.info(f"🖱️ fallback click AVÔ: {_describe_el(driver, grand)}")
            driver.execute_script("arguments[0].click();", grand)
            _sleep(0.10, 0.25)
            return True
    except Exception as e:
        logger.warning(f"Falha ao clicar no avô: {e}")
    return False


# =========================
# Bloqueio / rate limit helpers
# =========================
_BLOCK_PATTERNS_PT = [
    "Ação bloqueada",
    "Limitamos com que frequência",
    "Tente novamente mais tarde",
    "Não foi possível concluir",
    "Limite de tentativas",
]
_BLOCK_PATTERNS_EN = [
    "Action blocked",
    "We limit how often",
    "Try again later",
    "Couldn't complete your request",
    "We restrict certain activity",
]


def _detect_action_blocked(driver: WebDriver) -> bool:
    """Detecta sinais de bloqueio/limite na UI (PT/EN)."""
    try:
        # Áreas comuns de banners/alerts/dialogs
        nodes = []
        nodes += _xpath_all(driver, "//*[@role='alert' or @role='status']")
        nodes += _xpath_all(
            driver, "//*[@aria-live='polite' or @aria-live='assertive']"
        )
        nodes += _xpath_all(driver, "//*[@role='dialog']//*[not(self::script)]")
        # Varredura leve por fragments (limita a 200 nós para não custar caro)
        scans = nodes[:200]
        for n in scans:
            try:
                txt = (n.text or "").strip()
                if not txt:
                    continue
                for frag in _BLOCK_PATTERNS_PT:
                    if frag.lower() in txt.lower():
                        logger.info(f"🚫 bloqueio detectado (PT): {txt!r}")
                        return True
                for frag in _BLOCK_PATTERNS_EN:
                    if frag.lower() in txt.lower():
                        logger.info(f"🚫 bloqueio detectado (EN): {txt!r}")
                        return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _cooldown_on_block() -> None:
    # Padrão conservador: 10 a 30 minutos
    cmin = _env_int("ACTION_BLOCK_COOLDOWN_MIN", 600)
    cmax = _env_int("ACTION_BLOCK_COOLDOWN_MAX", 1800)
    if cmax < cmin:
        cmax = cmin
    logger.info(
        f"🧊 cooldown por bloqueio acionado: aguardando {cmin}-{cmax}s antes de retomar."
    )
    _sleep(cmin, cmax)


# =========================
# Comentário helpers
# =========================
def _find_comment_textarea_simple(driver: WebDriver):
    """Procura *apenas* textarea pelos rótulos que você especificou (PT/EN, … e ...)."""
    css_order = [TA_PT_THREEDOTS, TA_PT_ELLIPSIS, TA_EN_THREEDOTS, TA_EN_ELLIPSIS]
    for css in css_order:
        el = _js_query(driver, css)
        logger.info(f"🔎 textarea via CSS '{css}' -> {'OK' if el else 'nada'}")
        if el:
            logger.info(f"   alvo: {_describe_el(driver, el)}")
            return el
    fallback = _js_query(
        driver,
        "textarea[aria-label*='coment'],textarea[aria-label*='Coment'],"
        "textarea[aria-label*='comment'],textarea[aria-label*='Comment']",
    )
    if fallback:
        logger.info(f"   fallback textarea: {_describe_el(driver, fallback)}")
    else:
        logger.info("   nenhum textarea encontrado pelos padrões definidos.")
    return fallback


def _find_post_button(driver: WebDriver):
    """Procura o botão 'Post'/'Publicar' na UI nova (div role=button)."""
    xpaths = [
        POST_BTN_XP_EN,
        POST_BTN_XP_PT,
        POST_BTN_XP_EN_SPAN,
        POST_BTN_XP_PT_SPAN,
        # fallback genérico:
        "//button[@type='submit' and not(@disabled)]",
    ]
    for xp in xpaths:
        el = _xpath_one(driver, xp)
        logger.info(
            f"🔎 procurando botão de publicar com XPath: {xp} -> {'OK' if el else 'nada'}"
        )
        if el:
            logger.info(f"   post button alvo: {_describe_el(driver, el)}")
            return el
    return None


# =========================
# Ações públicas
# =========================
def do_like(
    driver: WebDriver, target: Dict, *, profile_dir: Optional[str] = None
) -> bool:
    if not _navigate_to_target(driver, target):
        return False

    # checa bloqueio antes de tentar
    if _detect_action_blocked(driver):
        _cooldown_on_block()
        return False

    if _already_liked(driver):
        logger.info("Post já curtido — marcando como consumido e pulando.")
        mark_target_consumed(profile_dir, target.get("id", target.get("url", "")))
        return True

    candidates = _gather_like_candidates(driver)
    if not candidates:
        logger.info("❌ nenhum candidato de like encontrado (SVG 24x24).")
        return False

    # tenta até 2 candidatos diferentes antes de desistir (evita spam de cliques)
    attempts = 0
    for sel, el in candidates:
        attempts += 1
        logger.info(f"tentando clicar candidato '{sel}' -> {_describe_el(driver, el)}")
        ok = _click_svg_like(driver, el)
        logger.info(f"resultado do clique: {'SUCESSO' if ok else 'FALHA'}")
        if not ok:
            if _detect_action_blocked(driver):
                _cooldown_on_block()
                return False
            if attempts >= 2:
                break
            continue

        # confirmação de estado
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
            "⚠️ clique executado, mas não confirmou 'Descurtir' — verificando bloqueio e/ou tentando próximo…"
        )
        if _detect_action_blocked(driver):
            _cooldown_on_block()
            return False

        if attempts >= 2:
            break

    logger.info("❌ esgotou candidatos de like sem confirmação.")
    return False


def do_comment(
    driver: WebDriver, target: Dict, text: str, *, profile_dir: Optional[str] = None
) -> bool:
    """
    Comentário usando a mesma lógica de digitação “humana”:
    - encontra exatamente o textarea correto (PT/EN, … e ...)
    - clica para focar, garante foco e digita com _human_type
    - tenta clicar no botão 'Post/Publicar' (UI nova). Se não achar, ENTER.
    - confirma publicação.
    """
    if not text or not text.strip():
        logger.info("❌ comentário vazio — pulando.")
        return False

    if not _navigate_to_target(driver, target):
        return False

    # checa bloqueio antes
    if _detect_action_blocked(driver):
        _cooldown_on_block()
        return False

    textarea = _find_comment_textarea_simple(driver)
    if not textarea:
        logger.info("❌ textarea de comentário não encontrada.")
        return False

    try:
        _highlight(driver, textarea, "red")
        textarea.click()
        _sleep(0.12, 0.30)
        textarea.click()  # alguns layouts expandem no segundo clique
        _sleep(0.08, 0.16)
        driver.execute_script("arguments[0].focus();", textarea)
    except Exception as e:
        logger.info(f"⚠️ foco inicial falhou: {e}")

    try:
        is_active = driver.execute_script(
            "return document.activeElement === arguments[0];", textarea
        )
        logger.info(f"   document.activeElement == textarea? {bool(is_active)}")
        if not is_active:
            textarea.click()
            _sleep(0.08, 0.16)
    except Exception:
        pass

    txt = text.strip()
    logger.info(f"⌨️ digitando comentário ({len(txt)} chars)")
    try:
        _human_type(textarea, txt, min_delay=0.03, max_delay=0.12)
    except Exception as e:
        logger.warning(f"Falha no send_keys direto: {e}")
        try:
            active = driver.switch_to.active_element
            _human_type(active, txt, min_delay=0.03, max_delay=0.12)
        except Exception as e2:
            logger.warning(f"Falha no activeElement: {e2}")
            return False

    _sleep(0.20, 0.45)

    # Preferir botão "Post"/"Publicar" (UI nova); senão ENTER
    post_btn = _find_post_button(driver)
    if post_btn:
        try:
            _highlight(driver, post_btn, "red")
            logger.info("🖱️ clicando no botão de publicar")
            _sleep(0.12, 0.28)  # pequeno delay antes do clique
            driver.execute_script("arguments[0].click();", post_btn)
        except Exception as e:
            logger.warning(f"Falha ao clicar no botão Post/Publicar: {e}; usando ENTER")
            try:
                textarea.send_keys(Keys.ENTER)
                logger.info("↩️ ENTER enviado (fallback)")
            except Exception:
                pass
    else:
        try:
            textarea.send_keys(Keys.ENTER)
            logger.info("↩️ ENTER enviado")
        except Exception as e:
            logger.warning(f"Falha ao enviar ENTER: {e}")

    _sleep(0.7, 1.2)

    # Checa bloqueio pós-envio
    if _detect_action_blocked(driver):
        _cooldown_on_block()
        return False

    # Confirmação
    try:
        val = textarea.get_attribute("value") or ""
        logger.info(f"   pós-envio, length do textarea={len(val)}")
        if val.strip() == "":
            mark_target_consumed(profile_dir, target.get("id", target.get("url", "")))
            logger.info(
                "✅ comentário aparentemente publicado (textarea vazio após envio)."
            )
            return True
    except Exception:
        pass

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
