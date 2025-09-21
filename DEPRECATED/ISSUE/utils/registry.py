import json, time
from pathlib import Path
from typing import Dict, Set, Optional


def registry_paths(base_dir: str):
    bd = Path(base_dir)
    bd.mkdir(parents=True, exist_ok=True)
    return bd / "used_urls.txt", bd / "actions.jsonl"


def load_used(base_dir: str) -> Set[str]:
    used_txt, _ = registry_paths(base_dir)
    if not used_txt.exists():
        return set()
    return set(
        [
            ln.strip()
            for ln in used_txt.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    )


def mark_used(base_dir: str, url: str, record: Dict):
    used_txt, actions = registry_paths(base_dir)
    used = []
    if used_txt.exists():
        used = [
            ln.strip()
            for ln in used_txt.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    used.append(url)
    used_txt.write_text("\n".join(used), encoding="utf-8")
    with actions.open("a", encoding="utf-8") as f:
        f.write(
            json.dumps({**record, "ts": int(time.time())}, ensure_ascii=False) + "\n"
        )
