# utils/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class Config:
    # -------- Execução / fluxo (pensado para janela de 6h) --------
    # Limite duro de ações por perfil na janela de execução (6h)
    # Seguro para conta nova/conservadora
    max_actions_per_profile: int = 100

    # Quantos alvos buscar por rodada de coleta (mantém navegação suave)
    fetch_batch_size: int = 24

    # Pool inicial de links coletados no startup (evita reuso e “rajada”)
    max_collected_links_startup: int = 150

    # -------- Pausas humanas (segundos) — sempre (min, max) --------
    # Pausa entre ações principais (like OU comment).
    # Com média ~150s, 6h ≈ 144 slots teóricos; o max_actions_per_profile corta em 100 antes.
    pause_between_actions: Tuple[float, float] = (90.0, 210.0)

    # Pausas leves durante scroll/coleta (em páginas de tag/explore)
    scroll_and_fetch_interval: Tuple[float, float] = (2.5, 5.0)

    # Atraso inicial por perfil ao iniciar (evita “partida sincronizada”)
    profile_start_stagger_range_seconds: Tuple[float, float] = (5.0, 15.0)

    # -------- Ações (somente like/comment conforme escopo atual) --------
    # Menos comentários que likes = mais seguro para conta nova
    actions_distribution: Dict[str, float] = field(
        default_factory=lambda: {
            "like": 0.7,
            "comment": 0.3,
        }
    )
    # Se não houver texto de comentário disponível, cai para like
    comment_fallback_to_like: bool = True

    # -------- Conteúdo-alvo --------
    # Hashtags base — ajuste à sua estratégia; a coleta usa /explore/tags/<tag>
    tags: List[str] = field(default_factory=lambda: ["colombia", "peru", "venezuela"])
    # Mantido para possível expansão futura (não usado no fluxo atual)
    locations: List[str] = field(default_factory=list)

    # -------- Geolocalização --------
    use_geolocation_override: bool = True
    geo_lat: float = -22.8268  # São Gonçalo (RJ)
    geo_lon: float = -43.0634
    geo_acc: int = 120  # metros


# Singleton simples para evitar recriar config
_cfg_singleton: Config | None = None


def get_config() -> Config:
    global _cfg_singleton
    if _cfg_singleton is None:
        cfg = Config()

        # Sanidade: manter apenas chaves suportadas nas ações
        supported = {"like", "comment"}
        cfg.actions_distribution = {
            k: float(v) for k, v in cfg.actions_distribution.items() if k in supported
        }
        # Garantir que exista pelo menos uma ação válida
        if not cfg.actions_distribution:
            cfg.actions_distribution = {"like": 1.0}

        # Normalizar pesos
        total = sum(cfg.actions_distribution.values()) or 1.0
        cfg.actions_distribution = {
            k: v / total for k, v in cfg.actions_distribution.items()
        }

        # Normalizar/limpar tags
        cfg.tags = [t.strip() for t in cfg.tags if isinstance(t, str) and t.strip()]

        _cfg_singleton = cfg
    return _cfg_singleton
