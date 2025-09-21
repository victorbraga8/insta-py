from collections import Counter
import random
CONFIG_INDIVIDUAIS = {"like": 6,"follow": 3,"stories": 3,"comentario": 3}
CONFIG_COMBINADAS = {"like+stories": 2,"follow+comentario": 0,"like+follow+stories": 0}
ACOES_REQUEREM_LINK = {"like","follow","comentario"}
def metas_por_acao():
    metas = Counter(CONFIG_INDIVIDUAIS)
    for combo, q in CONFIG_COMBINADAS.items():
        for a in combo.split('+'):
            metas[a] += int(q)
    return metas
def gerar_fila():
    tokens = []
    for a, q in CONFIG_INDIVIDUAIS.items():
        tokens.extend([a]*int(q))
    for combo, q in CONFIG_COMBINADAS.items():
        tokens.extend([tuple(combo.split('+'))]*int(q))
    random.shuffle(tokens); return tokens
