import json, os
from typing import List, Set
DB_PATH = os.getenv("INTERACTIONS_DB", "data/interacted_links.json")
def _ensure_file():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    if not os.path.exists(DB_PATH):
        with open(DB_PATH,"w",encoding="utf-8") as f: json.dump({"seen":[]}, f)
def load_seen()->Set[str]:
    _ensure_file()
    with open(DB_PATH,"r",encoding="utf-8") as f: data=json.load(f)
    return set(data.get("seen",[]))
def save_seen(seen:Set[str]):
    _ensure_file()
    with open(DB_PATH,"w",encoding="utf-8") as f: json.dump({"seen":sorted(list(seen))}, f, ensure_ascii=False)
def filter_unseen(links: List[str])->List[str]:
    seen = load_seen(); return [l for l in links if l not in seen]
def mark_seen(links: List[str]):
    seen = load_seen(); seen.update(links); save_seen(seen)
