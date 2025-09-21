import os, time, random, traceback, threading
from pathlib import Path
from typing import List, Optional
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import InvalidSessionIdException, WebDriverException

from utils.actions import (
    load_comments_pool,
    mark_comment_used,
    like_post,
    comment_post,
    settle_page,  # importante: clicar dentro do DOM após navegação
)
from utils.registry import load_used, mark_used
from utils.strategy import StrategyPlan
from utils.logger import Logger

NAV_MIN = int(os.getenv("NAVIGATE_MIN_MS", "700"))
NAV_MAX = int(os.getenv("NAVIGATE_MAX_MS", "1500"))
ACT_MIN = int(os.getenv("ACTION_AFTER_MIN_MS", "800"))
ACT_MAX = int(os.getenv("ACTION_AFTER_MAX_MS", "1600"))

# aguardo pós-clique de “assentar página” (para tirar foco da URL)
SETTLE_MIN_MS = int(os.getenv("SETTLE_MIN_MS", "3000"))
SETTLE_MAX_MS = int(os.getenv("SETTLE_MAX_MS", "4500"))

DEBUG_VISUAL = os.getenv("DEBUG_VISUAL", "false").lower() == "true"
DEBUG_MS = int(os.getenv("DEBUG_MS", "600"))


def _ms(n: int, stop_event: Optional[threading.Event] = None):
    """Sleep em ms respeitando stop_event."""
    end = time.time() + n / 1000.0
    while time.time() < end:
        if stop_event and stop_event.is_set():
            return
        time.sleep(0.05)


def _read_links(out_dir: str, tags: List[str]) -> List[str]:
    urls = []
    for tag in tags:
        p = Path(out_dir) / f"{tag.strip('#').lower()}.txt"
        if p.exists():
            urls += [
                ln.strip()
                for ln in p.read_text(encoding="utf-8").splitlines()
                if ln.strip()
            ]
    dedup = []
    seen = set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            dedup.append(u)
    random.shuffle(dedup)
    return dedup


def _debug_overlay(driver, msg: str):
    if not DEBUG_VISUAL:
        return
    try:
        driver.execute_script(
            """
            (function(msg,ms){
                try {
                    let box = document.getElementById('__dbg_overlay');
                    if (!box) {
                        box = document.createElement('div');
                        box.id='__dbg_overlay';
                        box.style.position='fixed';
                        box.style.top='10px';
                        box.style.left='10px';
                        box.style.padding='8px 10px';
                        box.style.background='rgba(0,0,0,0.7)';
                        box.style.color='#fff';
                        box.style.font='12px/1.3 monospace';
                        box.style.zIndex='2147483647';
                        box.style.borderRadius='8px';
                        box.style.boxShadow='0 2px 8px rgba(0,0,0,0.35)';
                        document.body.appendChild(box);
                    }
                    box.textContent = msg;
                    setTimeout(()=>{ try{ box.remove(); }catch(e){} }, ms||600);
                } catch(e) {}
            })(arguments[0], arguments[1]);
            """,
            msg,
            DEBUG_MS,
        )
    except Exception:
        pass


def _perform(
    driver,
    url: str,
    action: str,
    comments_pool: List[str],
    type_lo: int,
    type_hi: int,
    type_err: float,
    post_pause: int,
    stop_event: Optional[threading.Event] = None,
) -> str:
    try:
        if stop_event and stop_event.is_set():
            return "abort"

        # ---- Navegação protegida: se o WebDriver caiu, aborta sem estourar stack
        try:
            driver.get(url)
        except Exception as e:
            msg = f"{e!r}"
            # sinais comuns quando o chromium/webdriver já morreu
            if (
                "MaxRetryError" in msg
                or "Failed to establish a new connection" in msg
                or "Connection refused" in msg
                or "ERR_CONNECTION_REFUSED" in msg
                or "ConnectionResetError" in msg
            ):
                return "abort"
            # outros erros seguem o tratamento normal
            raise

        # >>> clicamos dentro do DOM e esperamos antes de agir (mata foco da URL)
        try:
            settle_page(driver, SETTLE_MIN_MS, SETTLE_MAX_MS)
        except Exception:
            pass

        if stop_event and stop_event.is_set():
            return "abort"

        _debug_overlay(driver, f"nav → {action}")

        # Aguarda corpo presente; se stop acionado, aborta cedo
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except Exception as e:
            # Se nem o <body> aparece, algo está errado com a sessão/guia
            return "abort"

        _ms(random.randint(260, 620), stop_event)

        if stop_event and stop_event.is_set():
            return "abort"

        if action == "like":
            ok = like_post(driver)
            _debug_overlay(driver, f"like → {'ok' if ok else 'fail'}")
            _ms(random.randint(ACT_MIN, ACT_MAX), stop_event)
            return "ok" if ok else "fail"

        if action == "comment":
            if not comments_pool:
                return "no-comment"
            text = comments_pool.pop()
            ok = comment_post(driver, text, type_lo, type_hi, type_err, post_pause)
            _debug_overlay(driver, f"comment → {'ok' if ok else 'fail'}")
            _ms(random.randint(ACT_MIN, ACT_MAX), stop_event)
            return f"ok:{text}" if ok else "fail"

        if action == "combo":
            if not comments_pool:
                return "no-comment"
            text = comments_pool.pop()
            ok_like = like_post(driver)
            _ms(random.randint(300, 700), stop_event)
            ok_c = comment_post(driver, text, type_lo, type_hi, type_err, post_pause)
            ok = ok_like and ok_c
            _debug_overlay(driver, f"combo → {'ok' if ok else 'fail'}")
            _ms(random.randint(ACT_MIN, ACT_MAX), stop_event)
            return f"ok:{text}" if ok else "fail"

        return "skip"

    except KeyboardInterrupt:
        return "abort"
    except (InvalidSessionIdException, WebDriverException):
        # sessão encerrada/driver morto
        return "abort"
    except Exception:
        # outras falhas específicas já são tratadas no caller via log
        raise


def run_actions(driver, profile_id: str, stop_event: Optional[threading.Event] = None):
    if stop_event and stop_event.is_set():
        return

    log = Logger(profile_id, base_dir=os.getenv("LOG_DIR", "data/logs"))
    out_dir = os.getenv("OUT_DIR", "data/links")
    reg_dir = os.getenv("REGISTRY_DIR", "data/registry")
    tags = [t.strip() for t in os.getenv("TAGS", "").split(",") if t.strip()]
    per_run_env = os.getenv("PER_RUN", "").strip()

    type_lo = int(os.getenv("TYPE_MIN_MS", "45"))
    type_hi = int(os.getenv("TYPE_MAX_MS", "120"))
    type_err = float(os.getenv("TYPE_MISTAKE_PROB", "0.02"))
    post_pause = int(os.getenv("POST_TYPE_PAUSE_MS", "350"))

    used = load_used(reg_dir)
    urls_all = [u for u in _read_links(out_dir, tags) if u not in used]

    plan = StrategyPlan(profile_id)

    # zera 'reels' se existir no plano por vestígios antigos
    if hasattr(plan, "exhaust") and callable(getattr(plan, "exhaust")):
        try:
            plan.exhaust("reels")
        except Exception:
            pass
    else:
        try:
            if (
                hasattr(plan, "_remaining")
                and isinstance(plan._remaining, dict)
                and "reels" in plan._remaining
            ):
                plan._remaining["reels"] = 0
        except Exception:
            pass

    total = {
        k: v for k, v in plan.total.copy().items() if k in ("like", "comment", "combo")
    }
    plan_total = sum(total.values())
    target_total = int(per_run_env) if per_run_env.isdigit() else plan_total

    comments_pool = load_comments_pool(
        "comentarios.txt",
        f"{reg_dir}/recent_comments.txt",
        int(os.getenv("COMMENTS_RECENT", "60")),
    )

    processed = 0
    i = 0
    log.info(f"início execução: alvo total {target_total} | cotas {total}")

    try:
        while processed < target_total:
            if stop_event and stop_event.is_set():
                log.info("stop_event acionado. finalizando loop.")
                break

            action = plan.next_action()
            if action == "none":
                break

            # ignore qualquer vestígio de 'reels'
            if action == "reels":
                if hasattr(plan, "exhaust") and callable(getattr(plan, "exhaust")):
                    try:
                        plan.exhaust("reels")
                    except Exception:
                        pass
                continue

            if plan.remaining().get(action, 0) <= 0:
                continue

            url = None
            while i < len(urls_all):
                if stop_event and stop_event.is_set():
                    break
                url = urls_all[i]
                i += 1
                break

            if stop_event and stop_event.is_set():
                log.info("stop_event acionado durante seleção de URL.")
                break

            if not url:
                log.info(f"sem URL disponível para ação {action}, pulando ação")
                if hasattr(plan, "exhaust") and callable(getattr(plan, "exhaust")):
                    try:
                        plan.exhaust(action)
                    except Exception:
                        pass
                else:
                    try:
                        if hasattr(plan, "_remaining") and isinstance(
                            plan._remaining, dict
                        ):
                            plan._remaining[action] = 0
                    except Exception:
                        pass
                continue

            try:
                res = _perform(
                    driver,
                    url,
                    action,
                    comments_pool,
                    type_lo,
                    type_hi,
                    type_err,
                    post_pause,
                    stop_event=stop_event,
                )

                if res == "abort":
                    log.info("sessão encerrada/execução abortada. finalizando loop.")
                    break

                if res.startswith("ok"):
                    plan.mark_done(action)
                    record = {"url": url, "profile": profile_id, "action": action}

                    if ":" in res:
                        text = res.split(":", 1)[1]
                        record["comment"] = text
                        mark_comment_used(
                            f"{reg_dir}/recent_comments.txt",
                            text,
                            int(os.getenv("COMMENTS_RECENT", "60")),
                        )

                    mark_used(reg_dir, url, record)
                    processed += 1
                    left = plan.remaining()
                    done = plan.done
                    log.progress(
                        done,
                        left,
                        {
                            "like": total.get("like", 0),
                            "comment": total.get("comment", 0),
                            "combo": total.get("combo", 0),
                        },
                    )

                elif res == "no-comment":
                    log.error(f"sem comentário disponível | ação {action} | url {url}")

                elif res in ("fail", "skip"):
                    log.error(f"falha em {action} | url {url}")

                _ms(random.randint(900, 1800), stop_event)

            except KeyboardInterrupt:
                log.info("interrompido pelo usuário (KeyboardInterrupt). finalizando.")
                break
            except (InvalidSessionIdException, WebDriverException):
                log.info("sessão WebDriver encerrada. finalizando.")
                break
            except Exception as e:
                tb = "".join(traceback.format_exc().splitlines()[-2:])
                log.error(f"exceção em {action} | url {url} | {e} | {tb}")
                _ms(1200, stop_event)

    finally:
        pass  # encerramento do driver é responsabilidade do caller

    left = plan.remaining()
    done = plan.done
    log.info(f"final execução | feitos {processed}/{target_total}")
    log.progress(
        done,
        left,
        {
            "like": total.get("like", 0),
            "comment": total.get("comment", 0),
            "combo": total.get("combo", 0),
        },
    )
