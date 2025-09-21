# utils/auth.py
from __future__ import annotations

import os
import time
import random
from pathlib import Path
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from utils.logger import get_logger
from utils.driver import wait_for_page_ready, set_geolocation_override

logger = get_logger("auth")


def _human_type(el, text: str, a: float = 0.04, b: float = 0.14) -> None:
    for ch in text:
        el.send_keys(ch)
        time.sleep(random.uniform(a, b))


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


# ---------- NOVO: validação de perfil/sessão ----------
def _profile_dir(session_dir: Optional[str]) -> Path:
    base = Path(os.getenv("SESSIONS_DIR", "sessions")).resolve()
    # padrão do orchestrator: sessions/default
    return Path(session_dir).resolve() if session_dir else (base / "default")


def _has_valid_profile(session_dir: Optional[str]) -> bool:
    """Considera 'logado' só se houver artefatos reais do perfil do Chrome."""
    p = _profile_dir(session_dir)
    if not p.exists():
        return False

    # Heurísticas de Chrome profile
    candidates = [
        p / "Local State",
        p / "Default",
        p / "Default" / "Preferences",
        p / "Default" / "Network",
        p / "Default" / "Cookies",
        p / "Default" / "Login Data",
    ]
    if any(path.exists() for path in candidates):
        return True

    # fallback: diretório não-vazio com > 3 entradas
    try:
        entries = sum(1 for _ in p.iterdir())
        return entries >= 3
    except Exception:
        return False


# ------------------------------------------------------


def _dismiss_popups(driver: WebDriver) -> None:
    try:
        btn = _find_visible(
            driver,
            By.XPATH,
            "//button[contains(., 'Agora não') or contains(., 'Not Now') or contains(., 'Não agora')]",
            timeout=2.0,
        )
        if btn:
            btn.click()
            time.sleep(0.4)
    except Exception:
        pass


def _perform_login_minimal(driver: WebDriver, username: str, password: str) -> bool:
    try:
        driver.get("https://www.instagram.com/accounts/login/")
        wait_for_page_ready(driver, timeout=10.0)
        time.sleep(random.uniform(0.5, 1.0))

        user_el = _find_visible(driver, By.NAME, "username", timeout=3.0)
        pass_el = _find_visible(driver, By.NAME, "password", timeout=3.0)

        if not user_el or not pass_el:
            # Se os campos sumiram, pode ser porque já estamos autenticados
            logger.info("Campos de login ausentes; pode já estar autenticado.")
            return True

        try:
            user_el.click()
            user_el.clear()
        except Exception:
            pass
        _human_type(user_el, username, 0.03, 0.10)
        time.sleep(random.uniform(0.2, 0.4))

        try:
            pass_el.click()
            pass_el.clear()
        except Exception:
            pass
        _human_type(pass_el, password, 0.04, 0.12)
        time.sleep(random.uniform(0.2, 0.4))

        try:
            btn = _find_visible(
                driver, By.CSS_SELECTOR, "button[type='submit']", timeout=1.5
            )
            if btn:
                btn.click()
            else:
                from selenium.webdriver.common.keys import Keys

                pass_el.send_keys(Keys.ENTER)
        except Exception:
            pass

        time.sleep(2.0)
        _dismiss_popups(driver)
        return True
    except Exception as e:
        logger.warning(f"Falha no login minimal: {e}")
        return False


def ensure_login(
    driver: WebDriver,
    username: str,
    password: str,
    session_dir: Optional[str] = None,
    force: bool = False,
) -> bool:
    # 1) Se há perfil válido, considera logado e sai.
    if _has_valid_profile(session_dir):
        logger.info("Sessão detectada via perfil válido em 'sessions' — pulando login.")
        return True

    try:
        set_geolocation_override(driver, -22.8268, -43.0634, 120)
        logger.info("Geolocalização aplicada: São Gonçalo (RJ)")
    except Exception:
        logger.warning("Falha ao aplicar geolocalização.")

    # 2) Tenta login apenas se não encontrou perfil válido
    ok = _perform_login_minimal(driver, username, password)

    # 3) Revalida a existência de perfil após login
    if _has_valid_profile(session_dir):
        logger.info("Sessão confirmada: artefatos de perfil presentes em 'sessions'.")
        return True

    if ok:
        logger.info("Login executado (mínimo). Seguindo sem confirmação adicional.")
        return True

    logger.warning("Não foi possível garantir sessão — login mínimo falhou.")
    return False
