# utils/action.py
from __future__ import annotations

import time
import random
from typing import Optional, Dict, Iterable

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.common.exceptions import WebDriverException

from utils.logger import get_logger, human_sleep, timeit
from utils.driver import wait_for_page_ready
from utils.collector import mark_target_consumed

logger = get_logger("action")


# ---------------------------
# Helpers
# ---------------------------
def _human_type(
    el, text: str, min_delay: float = 0.03, max_delay: float = 0.12
) -> None:
    for ch in text:
        el.send_keys(ch)
        time.sleep(random.uniform(min_delay, max_delay))


def _find_visible(driver: WebDriver, by, selector, timeout: float = 3.0):
    end = time.time() + timeout
    while time.time() < end:
        try:
            el = driver.find_element(by, selector)
            if el and el.is_displayed():
                return el
        except Exception:
            pass
        time.sleep(0.15)
    return None


def _find_all(driver: WebDriver, by, selector) -> Iterable:
    try:
        return driver.find_elements(by, selector)
    except Exception:
        return []


def _navigate_to_target(driver: WebDriver, target: Dict) -> bool:
    url = target.get("url")
    if not url:
        return False
    try:
        driver.get(url)
    except WebDriverException:
        try:
            driver.get(url)
        except Exception as e:
            logger.warning(f"Falha ao navegar para {url}: {e}")
            return False

    wait_for_page_ready(driver, timeout=10.0)
    human_sleep((0.6, 1.2), reason="estabilizar DOM", logger=logger)

    # banner de cookies comum
    try:
        btn = _find_visible(
            driver,
            By.XPATH,
            "//button[contains(., 'Aceitar todos') or contains(., 'Accept all') or contains(., 'Permitir todos') or contains(., 'Allow all')]",
            timeout=1.0,
        )
        if btn:
            btn.click()
            human_sleep((0.2, 0.4), reason="fechar banner", logger=logger)
    except Exception:
        pass

    return True


def _avoid_liked_by_redirect(driver: WebDriver) -> None:
    try:
        if "/liked_by/" in (driver.current_url or ""):
            logger.info("Redirecionado para '/liked_by/'. Voltando…")
            driver.back()
            wait_for_page_ready(driver, timeout=6.0)
            human_sleep((0.4, 0.8), reason="retorno de liked_by", logger=logger)
    except Exception:
        pass


# ---------- UI highlight ----------
def _highlight_element(
    driver: WebDriver,
    el,
    *,
    color: str = "red",
    duration_ms: int = 1400,
    label: str = "",
) -> None:
    """
    Desenha um retângulo de destaque (borda e glow) sobre o elemento na viewport.
    - color: 'red' para clique / 'yellow' para skip etc.
    - duration_ms: tempo em ms que o overlay fica visível
    - label: texto opcional exibido acima do retângulo
    """
    try:
        driver.execute_script(
            """
            (function(el, color, duration, label) {
              try {
                const rect = el.getBoundingClientRect();
                const d = document;
                const overlay = d.createElement('div');
                overlay.setAttribute('data-debug-overlay', 'true');
                overlay.style.position = 'fixed';
                overlay.style.left = rect.left + 'px';
                overlay.style.top = rect.top + 'px';
                overlay.style.width = rect.width + 'px';
                overlay.style.height = rect.height + 'px';
                overlay.style.border = '3px solid ' + color;
                overlay.style.borderRadius = '14px';
                overlay.style.boxShadow = '0 0 0 4px rgba(0,0,0,0.15), 0 0 16px 4px ' + color;
                overlay.style.pointerEvents = 'none';
                overlay.style.zIndex = 2147483647;
                overlay.style.transition = 'opacity 150ms ease-out';
                overlay.style.opacity = '1';

                let caption;
                if (label && label.length) {
                  caption = d.createElement('div');
                  caption.textContent = label;
                  caption.style.position = 'fixed';
                  caption.style.left = rect.left + 'px';
                  caption.style.top = Math.max(8, rect.top - 26) + 'px';
                  caption.style.padding = '2px 6px';
                  caption.style.font = '12px/16px system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, Noto Sans, Helvetica, Arial';
                  caption.style.color = '#fff';
                  caption.style.background = color;
                  caption.style.borderRadius = '8px';
                  caption.style.pointerEvents = 'none';
                  caption.style.zIndex = 2147483647;
                  d.body.appendChild(caption);
                }

                d.body.appendChild(overlay);

                // leve animação
                overlay.animate(
                  [{ transform: 'scale(1.02)', opacity: 0.85 }, { transform: 'scale(1)', opacity: 1 }],
                  { duration: 200, easing: 'ease-out' }
                );

                setTimeout(() => {
                  overlay.style.opacity = '0';
                  if (caption) caption.style.opacity = '0';
                  setTimeout(() => {
                    overlay.remove();
                    if (caption) caption.remove();
                  }, 180);
                }, Math.max(200, duration));
              } catch (e) { /* noop */ }
            })(arguments[0], arguments[1], arguments[2], arguments[3]);
            """,
            el,
            color,
            int(duration_ms),
            label or "",
        )
    except Exception:
        # se não conseguir, apenas ignore — é feature de debug
        pass


# Seletores EXACTOS (PT-BR) conforme solicitado:
# - Comentário: textarea[aria-label="Adicione um comentário..."]
# - Like já aplicado (pular): svg[aria-label="Descurtir"][width="24"][height="24"]
# - Pode curtir:             svg[aria-label="Curtir"][width="24"][height="24"]


def _svg_unlike(driver: WebDriver):
    try:
        return _find_visible(
            driver,
            By.CSS_SELECTOR,
            'svg[aria-label="Descurtir"][width="24"][height="24"]',
            timeout=1.0,
        )
    except Exception:
        return None


def _svg_like(driver: WebDriver):
    try:
        return _find_visible(
            driver,
            By.CSS_SELECTOR,
            'svg[aria-label="Curtir"][width="24"][height="24"]',
            timeout=2.0,
        )
    except Exception:
        return None


def _click_svg(driver: WebDriver, svg_el) -> bool:
    try:
        # destaque antes do clique
        _highlight_element(
            driver, svg_el, color="red", duration_ms=900, label="clicando"
        )
        driver.execute_script("arguments[0].click();", svg_el)
        return True
    except Exception:
        return False


def _mark_consumed_if_possible(target: Dict, profile_dir: Optional[str]) -> None:
    try:
        if profile_dir and target.get("id"):
            mark_target_consumed(profile_dir, target["id"])
    except Exception:
        pass


# ---------------------------
# Public actions
# ---------------------------
def do_like(
    driver: WebDriver, target: Dict, *, profile_dir: Optional[str] = None
) -> bool:
    """
    Dá like se possível. Se já estiver curtido (Descurtir presente), apenas marca consumido.
    Mostra na UI o ícone que foi clicado (ou o que motivou o skip).
    """
    with timeit(logger, f"like {target.get('id') or target.get('url','')}"):
        if not _navigate_to_target(driver, target):
            return False

        _avoid_liked_by_redirect(driver)

        # Já curtido? destacar em AMARELO (skip) para debug
        s_unlike = _svg_unlike(driver)
        if s_unlike:
            _highlight_element(
                driver,
                s_unlike,
                color="gold",
                duration_ms=1000,
                label="já curtido (skip)",
            )
            logger.info("Post já curtido — pulando like.")
            _mark_consumed_if_possible(target, profile_dir)
            return True

        s_like = _svg_like(driver)
        if not s_like:
            logger.info("Ícone de 'Curtir' não encontrado.")
            return False

        if not _click_svg(driver, s_like):
            logger.info("Falha ao clicar no ícone de 'Curtir'.")
            return False

        # confirmação rápida: deve surgir o 'Descurtir'
        deadline = time.time() + 3.0
        while time.time() < deadline:
            human_sleep((0.25, 0.6), reason="confirmar like", logger=logger)
            _avoid_liked_by_redirect(driver)
            s_unlike = _svg_unlike(driver)
            if s_unlike:
                # destacar a confirmação também (curtido)
                _highlight_element(
                    driver, s_unlike, color="red", duration_ms=800, label="curtido"
                )
                _mark_consumed_if_possible(target, profile_dir)
                return True

        logger.info("Não foi possível confirmar o like.")
        return False


def do_comment(
    driver: WebDriver, target: Dict, text: str, *, profile_dir: Optional[str] = None
) -> bool:
    """
    Comenta usando exatamente o textarea com aria-label 'Adicione um comentário...'.
    Mostra na UI o textarea focado/acionado.
    """
    if not text or not text.strip():
        return False

    with timeit(logger, f"comment {target.get('id') or target.get('url','')}"):
        if not _navigate_to_target(driver, target):
            return False

        _avoid_liked_by_redirect(driver)

        textarea = _find_visible(
            driver,
            By.CSS_SELECTOR,
            'textarea[aria-label="Adicione um comentário..."]',
            timeout=3.0,
        )
        if not textarea:
            logger.info("Textarea de comentário não encontrada (PT-BR exato).")
            return False

        try:
            _highlight_element(
                driver,
                textarea,
                color="red",
                duration_ms=900,
                label="digitando comentário",
            )
            textarea.click()
        except Exception:
            pass

        human_sleep((0.15, 0.35), reason="foco no textarea", logger=logger)
        _human_type(textarea, text.strip(), min_delay=0.02, max_delay=0.09)
        human_sleep((0.2, 0.5), reason="pausa antes de enviar", logger=logger)

        try:
            textarea.send_keys(Keys.ENTER)
        except Exception:
            return False

        # confirmação leve: textarea vazio OU comentário visível
        deadline = time.time() + 4.0
        posted = False
        while time.time() < deadline:
            human_sleep((0.4, 0.8), reason="confirmar comentário", logger=logger)
            try:
                val = textarea.get_attribute("value") or ""
                if val.strip() == "":
                    posted = True
                    break
            except Exception:
                pass
            try:
                nodes = _find_all(
                    driver, By.XPATH, f"//*[contains(text(), {repr(text.strip())})]"
                )
                if nodes:
                    posted = True
                    break
            except Exception:
                pass

        if posted:
            # destaque curto pós-envio para depuração
            try:
                _highlight_element(
                    driver,
                    textarea,
                    color="red",
                    duration_ms=600,
                    label="comentário enviado",
                )
            except Exception:
                pass
            _mark_consumed_if_possible(target, profile_dir)
            return True

        logger.info("Não foi possível confirmar publicação do comentário.")
        return False
