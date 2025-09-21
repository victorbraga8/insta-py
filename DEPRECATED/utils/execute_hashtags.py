import logging
from collections import Counter, defaultdict
from typing import List
from utils.execute import executar_interacoes
from utils.hashtags import coletar_links_hashtag
from utils.state import filter_unseen, mark_seen
from utils.logger import espera_humana
from utils.settings import BETWEEN_TAGS_MIN, BETWEEN_TAGS_MAX
logger = logging.getLogger("interacoes")
def executar_por_hashtags(driver, hashtags: List[str], limite_por_tag: int = 60) -> dict:
    total = {"metas": Counter(), "feitos": Counter(), "erros": Counter(), "erros_itens": defaultdict(list), "total_executado": 0}
    for tag in hashtags:
        links = filter_unseen(coletar_links_hashtag(driver, tag, limite=limite_por_tag))
        logger.info(f"HASHTAG | #{tag} | links_coletados={len(links)}")
        parcial = executar_interacoes(driver, links); mark_seen(links)
        total["metas"].update(parcial["metas"]); total["feitos"].update(parcial["feitos"]); total["erros"].update(parcial["erros"])
        for k,v in parcial["erros_itens"].items(): total["erros_itens"][k].extend(v)
        total["total_executado"] += parcial["total_executado"]
        espera_humana(BETWEEN_TAGS_MIN, BETWEEN_TAGS_MAX)
    total["metas"]=dict(total["metas"]); total["feitos"]=dict(total["feitos"]); total["erros"]=dict(total["erros"])
    total["erros_itens"]={k:v for k,v in total["erros_itens"].items()}; logger.info(f"RESUMO_HASHTAGS | {total}"); return total
