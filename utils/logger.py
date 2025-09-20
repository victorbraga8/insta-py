import sys, time
from pathlib import Path


class Logger:
    def __init__(self, profile_id: str, base_dir: str = "data/logs"):
        ts = time.strftime("%Y%m%d")
        self.path = Path(base_dir) / f"{profile_id}_{ts}.log"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _w(self, level: str, msg: str):
        line = f"[{time.strftime('%H:%M:%S')}] {level} {msg}"
        print(line, flush=True)
        try:
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
        except Exception:
            pass

    def info(self, msg: str):
        self._w("INFO ", msg)

    def error(self, msg: str):
        self._w("ERROR", msg)

    def progress(self, done: dict, left: dict, total: dict):
        msg = (
            f"like {done.get('like',0)}/{total.get('like',0)} "
            f"comment {done.get('comment',0)}/{total.get('comment',0)} "
            f"combo {done.get('combo',0)}/{total.get('combo',0)} "
            f"reels {done.get('reels',0)}/{total.get('reels',0)} | "
            f"faltando: like {left.get('like',0)}, comment {left.get('comment',0)}, combo {left.get('combo',0)}, reels {left.get('reels',0)}"
        )
        self._w("PROG ", msg)
