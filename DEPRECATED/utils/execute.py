import os, logging
from collections import Counter, defaultdict, deque
from typing import Iterable, Union
from dotenv import load_dotenv
from utils.controle_acoes import gerar_fila, metas_por_acao, ACOES_REQUEREM_LINK
from utils.actions import realizar_acao
from utils.logger import espera_humana
from utils.settings import HUMAN_MIN, HUMAN_MAX
load_dotenv()
MAX_ACOES = int(os.getenv("MAX_ACOES", "0")) or None
logger = logging.getLogger("interacoes")
logger.setLevel(logging.INFO)
if not logger.handlers:
    import sys
    h = logging.StreamHandler(sys.stdout)
    f = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    h.setFormatter(f); logger.addHandler(h)

def _consumir_link(links_iter: Iterable[str]):
    try: return next(links_iter)
    except StopIteration: return None

def executar_interacoes(driver, links: Iterable[str]) -> dict:
    fila = deque(gerar_fila()); metas = metas_por_acao()
    feitos = Counter(); erros = Counter(); erros_itens = defaultdict(list)
    total = 0; links_iter = iter(links)
    while fila:
        token = fila.popleft()
        subacoes = (token,) if isinstance(token, str) else token
        for acao in subacoes:
            if MAX_ACOES is not None and total >= MAX_ACOES: break
            link = _consumir_link(links_iter) if acao in ACOES_REQUEREM_LINK else None
            ok, item = realizar_acao(driver, acao, link); total += 1
            if ok: feitos[acao]+=1
            else: erros[acao]+=1; erros_itens[acao].append(item or "")
            restantes = max(metas[acao]-feitos[acao]-erros[acao],0)
            status = "OK" if ok else "ERRO"
            logger.info(f"{status} {acao.upper()} | executadas={feitos[acao]}/{metas[acao]} | restantes={restantes} | erros={erros[acao]}" + (f" | item={item}" if not ok else ""))
            espera_humana()
        if MAX_ACOES is not None and total >= MAX_ACOES: break
    resumo = {"metas": dict(metas), "feitos": dict(feitos), "erros": dict(erros), "erros_itens": {k:v for k,v in erros_itens.items()}, "total_executado": total}
    logger.info(f"RESUMO | {resumo}"); return resumo
