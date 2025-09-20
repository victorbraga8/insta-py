import os, time, random, traceback
from pathlib import Path
from typing import List
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from utils.actions import (
    load_comments_pool,
    mark_comment_used,
    like_post,
    comment_post,
    view_reel,
)
from utils.registry import load_used, mark_used
from utils.strategy import StrategyPlan
from utils.logger import Logger


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


def _is_reel_url(url: str) -> bool:
    return "/reel/" in url


def _perform(
    driver,
    url: str,
    action: str,
    comments_pool: List[str],
    type_lo: int,
    type_hi: int,
    type_err: float,
    post_pause: int,
    view_min_ms: int,
    view_max_ms: int,
) -> str:
    driver.get(url)
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    time.sleep(random.uniform(0.25, 0.8))
    if action == "like":
        ok = like_post(driver)
        return "ok" if ok else "fail"
    if action == "comment":
        if not comments_pool:
            return "no-comment"
        text = comments_pool.pop()
        ok = comment_post(driver, text, type_lo, type_hi, type_err, post_pause)
        return f"ok:{text}" if ok else "fail"
    if action == "reels":
        if not _is_reel_url(url):
            return "skip"
        ok = view_reel(driver, view_min_ms, view_max_ms)
        return "ok" if ok else "fail"
    if action == "combo":
        if not comments_pool:
            return "no-comment"
        text = comments_pool.pop()
        ok_like = like_post(driver)
        time.sleep(random.uniform(0.4, 1.1))
        ok_c = comment_post(driver, text, type_lo, type_hi, type_err, post_pause)
        return f"ok:{text}" if (ok_like and ok_c) else "fail"
    return "skip"


def run_actions(driver, profile_id: str):
    log = Logger(profile_id, base_dir=os.getenv("LOG_DIR", "data/logs"))
    out_dir = os.getenv("OUT_DIR", "data/links")
    reg_dir = os.getenv("REGISTRY_DIR", "data/registry")
    tags = [t.strip() for t in os.getenv("TAGS", "").split(",") if t.strip()]
    per_run_env = os.getenv("PER_RUN", "").strip()
    type_lo = int(os.getenv("TYPE_MIN_MS", "45"))
    type_hi = int(os.getenv("TYPE_MAX_MS", "120"))
    type_err = float(os.getenv("TYPE_MISTAKE_PROB", "0.02"))
    post_pause = int(os.getenv("POST_TYPE_PAUSE_MS", "350"))
    view_min_ms = int(os.getenv("VIEW_MIN_MS", "6000"))
    view_max_ms = int(os.getenv("VIEW_MAX_MS", "12000"))
    used = load_used(reg_dir)
    urls_all = [u for u in _read_links(out_dir, tags) if u not in used]
    plan = StrategyPlan(profile_id)
    total = plan.total.copy()
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
    while processed < target_total:
        action = plan.next_action()
        if action == "none":
            break
        if plan.remaining().get(action, 0) <= 0:
            continue
        url = None
        while i < len(urls_all):
            cand = urls_all[i]
            i += 1
            if action == "reels" and not _is_reel_url(cand):
                continue
            url = cand
            break
        if not url:
            log.info(f"sem URL disponível para ação {action}, encerrando")
            break
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
                view_min_ms,
                view_max_ms,
            )
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
                log.progress(done, left, _recompute_totals(total))
            elif res == "no-comment":
                log.error(f"sem comentário disponível | ação {action} | url {url}")
            elif res in ("fail", "skip"):
                log.error(f"falha em {action} | url {url}")
            time.sleep(random.uniform(1.0, 2.2))
        except Exception as e:
            tb = "".join(traceback.format_exc().splitlines()[-2:])
            log.error(f"exceção em {action} | url {url} | {e} | {tb}")
            time.sleep(1.2)
    left = plan.remaining()
    done = plan.done
    log.info(f"final execução | feitos {processed}/{target_total}")
    log.progress(done, left, _recompute_totals(total))


def _recompute_totals(total):
    return {
        "like": total.get("like", 0),
        "comment": total.get("comment", 0),
        "combo": total.get("combo", 0),
        "reels": total.get("reels", 0),
    }
