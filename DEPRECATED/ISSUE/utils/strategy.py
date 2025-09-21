import json, random
from pathlib import Path
from typing import Dict


def _load_json(p: Path):
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


class StrategyPlan:
    def __init__(self, profile_id: str, base_dir: str = "data"):
        self.profile_id = profile_id
        self.base = Path(base_dir)
        self.cfg = self._load_cfg()
        self.total = {k: int(v) for k, v in self.cfg.get("weights", {}).items()}
        for k in ("like", "comment", "combo", "reels"):
            self.total.setdefault(k, 0)
        combo = self.total.get("combo", 0)
        if combo > min(self.total.get("like", 0), self.total.get("comment", 0)):
            m = min(self.total.get("like", 0), self.total.get("comment", 0))
            self.total["combo"] = m
        self.done = {"like": 0, "comment": 0, "combo": 0, "reels": 0}
        self.plan = self._make_plan(self.total)

    def _load_cfg(self) -> Dict:
        p_profile = self.base / f"strategy_{self.profile_id}.json"
        p_global = self.base / "strategy.json"
        cfg = (
            _load_json(p_profile)
            or _load_json(p_global)
            or {"type": "weighted", "weights": {"like": 1, "comment": 1}}
        )
        t = cfg.get("type", "weighted").lower()
        w = cfg.get("weights", {})
        w = {k.lower(): int(v) for k, v in w.items() if int(v) > 0}
        return {"type": "weighted", "weights": w}

    def _make_plan(self, weights: Dict[str, int]):
        items = []
        for k, n in weights.items():
            items += [k] * n
        random.shuffle(items)
        return items

    def remaining(self) -> Dict[str, int]:
        like_left = max(0, self.total["like"] - self.done["like"] - self.done["combo"])
        comment_left = max(
            0, self.total["comment"] - self.done["comment"] - self.done["combo"]
        )
        combo_left = max(0, self.total["combo"] - self.done["combo"])
        reels_left = max(0, self.total["reels"] - self.done["reels"])
        return {
            "like": like_left,
            "comment": comment_left,
            "combo": combo_left,
            "reels": reels_left,
        }

    def has_quota(self, action: str) -> bool:
        r = self.remaining()
        if action == "combo":
            return r["combo"] > 0 and r["like"] > 0 and r["comment"] > 0
        return r.get(action, 0) > 0

    def next_action(self) -> str:
        while self.plan:
            a = self.plan.pop()
            if self.has_quota(a):
                return a
        for a in ("combo", "like", "comment", "reels"):
            if self.has_quota(a):
                return a
        return "none"

    def mark_done(self, action: str):
        if action == "combo":
            self.done["combo"] += 1
        elif action in self.done:
            self.done[action] += 1
