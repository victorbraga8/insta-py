# utils/logger.py
from __future__ import annotations

import os
import sys
import time
import math
import logging
import threading
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
from typing import Optional, Tuple

# ------------- Internals / Colors -------------
_COLORS = {
    "RESET": "\033[0m",
    "DIM": "\033[2m",
    "BOLD": "\033[1m",
    "GRAY": "\033[90m",
    "RED": "\033[31m",
    "GREEN": "\033[32m",
    "YELLOW": "\033[33m",
    "BLUE": "\033[34m",
    "CYAN": "\033[36m",
    "MAGENTA": "\033[35m",
}


def _supports_color() -> bool:
    return sys.stdout.isatty()


def _level_color(level: int) -> str:
    if level >= logging.ERROR:
        return _COLORS["RED"]
    if level >= logging.WARNING:
        return _COLORS["YELLOW"]
    if level >= logging.INFO:
        return _COLORS["GREEN"]
    return _COLORS["CYAN"]


def _now_iso() -> str:
    tzname = os.getenv("TZ", "UTC")
    try:
        # Apenas etiqueta, não convertemos fuso sem libs extras
        return datetime.now().strftime(f"%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


class _ConsoleFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        use_color = _supports_color()
        levelname = record.levelname
        name = record.name
        msg = record.getMessage()
        t = _now_iso()
        thread = threading.current_thread().name

        if use_color:
            lvlc = _level_color(record.levelno)
            namec = _COLORS["BLUE"]
            gray = _COLORS["GRAY"]
            reset = _COLORS["RESET"]
            return f"{gray}{t}{reset} {lvlc}{levelname:<7}{reset} {namec}{name}{reset} [{thread}] — {msg}"
        else:
            return f"{t} {levelname:<7} {name} [{thread}] — {msg}"


class _FileFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        t = _now_iso()
        thread = threading.current_thread().name
        msg = record.getMessage().replace("\n", " ").strip()
        return f"{t} | {record.levelname:<7} | {record.name} | {thread} | {msg}"


# ------------- Public: get_logger -------------
_LOGGERS_CACHE = {}


def get_logger(name: str = "app") -> logging.Logger:
    if name in _LOGGERS_CACHE:
        return _LOGGERS_CACHE[name]

    level_str = (os.getenv("LOG_LEVEL", "INFO") or "INFO").upper()
    level = getattr(logging, level_str, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False

    # Evitar handlers duplicados em reloads
    if not logger.handlers:
        # Console
        ch = logging.StreamHandler(stream=sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(_ConsoleFormatter())
        logger.addHandler(ch)

        # Arquivo (opcional)
        if os.getenv("LOG_TO_FILE", "false").strip().lower() in (
            "1",
            "true",
            "yes",
            "y",
            "on",
        ):
            log_file = os.getenv("LOG_FILE", "logs/app.log")
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            fh = RotatingFileHandler(
                log_file, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
            )
            fh.setLevel(level)
            fh.setFormatter(_FileFormatter())
            logger.addHandler(fh)

    _LOGGERS_CACHE[name] = logger
    return logger


# ------------- Public: Sleep with logging -------------
def _fmt_secs(s: float) -> str:
    ms = int(round((s - int(s)) * 1000))
    m = int(s) // 60
    sec = int(s) % 60
    return f"{m:02d}:{sec:02d}.{ms:03d}"


def human_sleep(
    rng: Tuple[float, float],
    *,
    reason: Optional[str] = None,
    logger: Optional[logging.Logger] = None,
) -> float:
    """
    Escolhe um valor uniforme no intervalo rng=(min,max), LOGA o plano de espera,
    aguarda e retorna a duração real usada (float em segundos).
    """
    log = logger or get_logger("sleep")
    a, b = float(rng[0]), float(rng[1])
    if b < a:
        a, b = b, a
    import random

    duration = random.uniform(a, b)
    label = f"antes de {reason}" if reason else "antes da próxima etapa"
    log.info(f"⏳ aguardando {duration:0.2f}s ({a:0.2f}–{b:0.2f}) {label}")
    time.sleep(duration)
    return duration


# ------------- Public: Timing (context manager) -------------
@contextmanager
def timeit(logger: Optional[logging.Logger], label: str):
    """
    Mede o tempo de um bloco de código.
    Uso:
        with timeit(logger, "like"):
            do_like(...)
    """
    log = logger or get_logger("timeit")
    start = time.perf_counter()
    try:
        yield
    finally:
        dur = time.perf_counter() - start
        log.info(f"⏱️ {label} concluído em {dur:.3f}s")


# ------------- Public: Action logging helpers -------------
def log_action_plan(
    logger: logging.Logger, profile_id: str, action: str, target_url: str
) -> None:
    logger.info(f"[{profile_id}] ação planejada: {action} → {target_url}")


def log_action_result(
    logger: logging.Logger, profile_id: str, action: str, success: bool, extra: str = ""
) -> None:
    status = "OK" if success else "FALHA"
    if extra:
        logger.info(f"[{profile_id}] resultado {action}: {status} — {extra}")
    else:
        logger.info(f"[{profile_id}] resultado {action}: {status}")


def log_collect_summary(
    logger: logging.Logger,
    profile_id: str,
    tags_or_locations,
    count: int,
    phase: str = "startup",
) -> None:
    logger.info(f"[{profile_id}] coleta({phase}) {tags_or_locations} → {count} alvos")


# ------------- Public: Structured one-liners -------------
def log_wait_before_action(
    logger: logging.Logger, profile_id: str, action: str, rng: Tuple[float, float]
) -> float:
    """Atalho específico para o orquestrador: loga e espera antes da ação."""
    return human_sleep(rng, reason=f"executar '{action}'", logger=logger)


def log_scroll_pause(logger: logging.Logger, rng: Tuple[float, float]) -> float:
    """Atalho para pausas de scroll/coleta."""
    return human_sleep(rng, reason="scroll/coleta", logger=logger)
