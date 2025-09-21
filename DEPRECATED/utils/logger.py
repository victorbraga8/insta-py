import logging, random, time
from utils.settings import HUMAN_MIN, HUMAN_MAX
logger = logging.getLogger("interacoes")
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    f = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    h.setFormatter(f)
    logger.addHandler(h)
def log(msg:str): logger.info(msg)
def espera_humana(a:float=None,b:float=None):
    lo = HUMAN_MIN if a is None else a
    hi = HUMAN_MAX if b is None else b
    time.sleep(random.uniform(lo,hi))
