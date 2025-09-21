# utils/orchestrator.py
import os
import signal
import random
import threading
import time
from collections import deque
from pathlib import Path
from typing import Dict, Iterator, Optional

from utils.config import get_config
from utils.driver import init_driver, close_driver
from utils.auth import ensure_login
from utils.collector import collect_for_tags, get_next_target
from utils.action import do_like, do_comment
from utils.logger import (
    get_logger,
    human_sleep,
    log_action_plan,
    log_action_result,
    log_collect_summary,
    log_wait_before_action,
    log_scroll_pause,
    timeit,
)

logger = get_logger("orchestrator")
cfg = get_config()

STOP_EVENT = threading.Event()
DRIVERS: Dict[str, any] = {}
DRIVERS_LOCK = threading.Lock()

SESSIONS_DIR = Path(os.getenv("SESSIONS_DIR", "sessions"))
SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
COMMENTS_FILE = Path(os.getenv("COMMENTS_FILE", "comentarios.txt"))


def _env_bool(key: str, default: bool = False) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


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


def _weighted_choice(d: Dict[str, float]) -> str:
    keys = list(d.keys())
    weights = list(d.values())
    total = sum(weights) or 1.0
    r = random.random() * total
    upto = 0.0
    for k, w in zip(keys, weights):
        if upto + w >= r:
            return k
        upto += w
    return keys[-1]


def _set_geolocation(driver):
    if not cfg.use_geolocation_override:
        return
    try:
        driver.execute_cdp_cmd(
            "Emulation.setGeolocationOverride",
            {
                "latitude": float(cfg.geo_lat),
                "longitude": float(cfg.geo_lon),
                "accuracy": int(cfg.geo_acc),
            },
        )
        logger.info(
            f"Geolocation override: {cfg.geo_lat},{cfg.geo_lon} (acc={cfg.geo_acc})"
        )
    except Exception as e:
        logger.warning(f"Falha ao aplicar geolocation via CDP: {e}")


def _profile_worker():
    user = os.getenv("IG_PROFILE", "").strip()
    pwd = os.getenv("IG_PASS", "").strip()
    if not user or not pwd:
        logger.error("Credenciais ausentes (IG_PROFILE / IG_PASS).")
        return

    session_dir = SESSIONS_DIR / "default"
    session_dir.mkdir(parents=True, exist_ok=True)

    # ----- Novos controles: timebox e soft-cap por hora -----
    timebox_hours = _env_float("ORCH_TIMEBOX_HOURS", 6.0)  # padrão 6h
    hourly_soft_cap = _env_int("ORCH_HOURLY_SOFT_CAP", 20)  # padrão 20 ações/h
    hourly_window_secs = 3600
    hourly_actions = deque()  # timestamps (time.time()) das últimas ações concluídas
    start_ts = time.time()
    deadline_ts = start_ts + (timebox_hours * 3600.0)

    try:
        driver = init_driver(
            headless=_env_bool("HEADLESS", False),
            window_size=(
                _env_int("WINDOW_WIDTH", 1280),
                _env_int("WINDOW_HEIGHT", 900),
            ),
            lang=os.getenv("LANG", "pt-BR"),
            user_agent=os.getenv("USER_AGENT", None),
            profile_dir=str(session_dir),
        )
    except Exception as e:
        logger.exception("[default] Erro ao iniciar driver: %s", e)
        return

    with DRIVERS_LOCK:
        DRIVERS["default"] = driver

    try:
        # Login / sessão
        try:
            with timeit(logger, "default ensure_login"):
                ok = ensure_login(
                    driver=driver,
                    username=user,
                    password=pwd,
                    session_dir=str(session_dir),
                )
            if ok:
                logger.info("[default] Login garantido ou sessão reaproveitada.")
            else:
                logger.warning(
                    "[default] ensure_login retornou False — encerrando worker."
                )
                return
        except Exception as e:
            logger.exception("[default] Erro crítico no ensure_login: %s", e)
            return

        # Pós-login: ir para Home e aguardar alguns segundos
        try:
            driver.get("https://www.instagram.com/")
        except Exception:
            pass
        human_sleep((4.8, 6.2), reason="aguardar pós-login na Home", logger=logger)

        # Aplicar geolocalização do config se habilitado (não conflita com auth)
        _set_geolocation(driver)

        # Atraso humano inicial por perfil (evita partida sincronizada)
        human_sleep(
            cfg.profile_start_stagger_range_seconds,
            reason="profile start stagger",
            logger=logger,
        )

        # Coleta inicial (tags/locations)
        try:
            with timeit(logger, "default coleta_inicial"):
                collected = collect_for_tags(
                    driver=driver,
                    tags=cfg.tags,  # usa TODAS as tags do array
                    locations=cfg.locations,
                    max_links=cfg.max_collected_links_startup,
                    profile_dir=str(session_dir),
                )
            log_collect_summary(
                logger,
                "default",
                cfg.tags or cfg.locations,
                len(collected),
                phase="startup",
            )
        except Exception as e:
            logger.exception("[default] Falha na coleta inicial: %s", e)
            collected = []

        actions_done = 0
        used_targets = set()
        collected_iter: Iterator[dict] = iter(collected)

        while not STOP_EVENT.is_set() and actions_done < cfg.max_actions_per_profile:
            # ----- Checagem de timebox (6h por padrão) -----
            now = time.time()
            if now >= deadline_ts:
                elapsed = now - start_ts
                logger.info(
                    f"[default] Timebox atingido ({elapsed/3600:.2f}h). Encerrando worker."
                )
                break

            # ----- Soft-cap por hora (janela deslizante de 60min) -----
            # Remove timestamps fora da janela de 1h
            while hourly_actions and (now - hourly_actions[0] > hourly_window_secs):
                hourly_actions.popleft()

            if len(hourly_actions) >= hourly_soft_cap:
                # Cooldown humano para aliviar a taxa
                cooldown_range = (300.0, 600.0)  # 5 a 10 minutos
                logger.info(
                    f"[default] Soft-cap horário atingido "
                    f"({len(hourly_actions)}/{hourly_soft_cap}). "
                    f"Cooldown por {int(cooldown_range[0])}-{int(cooldown_range[1])}s."
                )
                human_sleep(
                    cooldown_range, reason="hourly soft-cap cooldown", logger=logger
                )
                # Após cooldown, revalida timebox e continua o loop
                continue

            # ----- Selecionar próximo alvo -----
            target: Optional[dict] = None
            try:
                # Próximo target não utilizado
                while True:
                    cand = get_next_target(collected_iter)
                    if cand is None:
                        break
                    if cand.get("id") not in used_targets:
                        target = cand
                        break

                # Recoleta incremental se esgotou
                if target is None:
                    try:
                        with timeit(logger, "default recolha_incremental"):
                            more = collect_for_tags(
                                driver=driver,
                                tags=cfg.tags,
                                locations=cfg.locations,
                                max_links=cfg.fetch_batch_size,
                                profile_dir=str(session_dir),
                            )
                        if more:
                            collected_iter = iter(more)
                            log_collect_summary(
                                logger,
                                "default",
                                (cfg.tags or cfg.locations),
                                len(more),
                                phase="incremental",
                            )
                            # volta ao topo do while para pegar o novo target
                            continue
                        else:
                            logger.info(
                                "[default] Sem novos targets. Encerrando worker."
                            )
                            break
                    except Exception as e:
                        logger.exception("[default] Erro na recolha incremental: %s", e)
                        break
            except Exception as e:
                logger.exception("[default] Erro obtendo próximo target: %s", e)
                break

            if not target or "url" not in target:
                log_scroll_pause(logger, cfg.scroll_and_fetch_interval)
                continue

            target_id = target.get("id") or target.get("url")
            target_url = target.get("url", "")
            used_targets.add(target_id)
            action = _weighted_choice(cfg.actions_distribution)

            log_action_plan(logger, "default", action, target_url)
            log_wait_before_action(logger, "default", action, cfg.pause_between_actions)

            try:
                with timeit(logger, f"default {action}"):
                    if action == "like":
                        ok = do_like(
                            driver=driver, target=target, profile_dir=str(session_dir)
                        )
                    elif action == "comment":
                        text = ""
                        if COMMENTS_FILE.exists():
                            with COMMENTS_FILE.open("r", encoding="utf-8") as f:
                                lines = [l.strip() for l in f if l.strip()]
                            if lines:
                                text = random.choice(lines)
                        if not text and cfg.comment_fallback_to_like:
                            ok = do_like(
                                driver=driver,
                                target=target,
                                profile_dir=str(session_dir),
                            )
                        else:
                            ok = do_comment(
                                driver=driver,
                                target=target,
                                text=text,
                                profile_dir=str(session_dir),
                            )
                    else:
                        logger.warning(
                            f"[default] Ação '{action}' não suportada. Pulando."
                        )
                        ok = False

                log_action_result(logger, "default", action, ok)
                if ok:
                    actions_done += 1
                    # registra timestamp desta ação concluída para a janela horária
                    hourly_actions.append(time.time())

            except Exception as e:
                logger.exception(f"[default] Erro executando '{action}': {e}")

        logger.info(
            f"[default] Finalizado. Ações realizadas: {actions_done} "
            f"(janela real: {(time.time()-start_ts)/3600:.2f}h)."
        )

    finally:
        with DRIVERS_LOCK:
            drv = DRIVERS.pop("default", None)
        try:
            close_driver(drv)
        except Exception:
            pass


def _handle_signal(signum, frame):
    logger.info(f"Sinal {signum} recebido. Encerrando…")
    STOP_EVENT.set()


signal.signal(signal.SIGINT, _handle_signal)
signal.signal(signal.SIGTERM, _handle_signal)


def run():
    logger.info("Iniciando orquestração")
    t = threading.Thread(target=_profile_worker, daemon=True, name="worker-default")
    t.start()
    try:
        while t.is_alive():
            t.join(timeout=1.0)
            if STOP_EVENT.is_set():
                break
    except KeyboardInterrupt:
        STOP_EVENT.set()
    finally:
        with DRIVERS_LOCK:
            for k, drv in list(DRIVERS.items()):
                try:
                    close_driver(drv)
                except Exception:
                    pass
                DRIVERS.pop(k, None)
        logger.info("Drivers encerrados.")
    logger.info("Encerrado")
