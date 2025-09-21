# utils/config.py
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class Config:
    # -------- Execução / fluxo --------
    max_actions_per_profile: int = 12
    fetch_batch_size: int = 12
    max_collected_links_startup: int = 18

    # Pausas humanas (segundos) — sempre (min, max)
    pause_between_actions: Tuple[float, float] = (6.5, 11.0)
    scroll_and_fetch_interval: Tuple[float, float] = (1.0, 2.0)
    profile_start_stagger_range_seconds: Tuple[float, float] = (1.5, 3.0)

    # -------- Ações (somente like/comment conforme escopo atual) --------
    actions_distribution: Dict[str, float] = field(
        default_factory=lambda: {
            "like": 0.6,
            "comment": 0.4,
        }
    )
    comment_fallback_to_like: bool = (
        True  # se não houver texto, curte em vez de comentar
    )

    # -------- Conteúdo-alvo --------
    # Use qualquer lista aqui; ex.: ["argentina", "uruguai", "brazil"]
    tags: List[str] = field(default_factory=lambda: ["paraguai", "uruguai", "brazil"])
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

        # Normalizar pesos (opcional, mas útil)
        total = sum(cfg.actions_distribution.values()) or 1.0
        cfg.actions_distribution = {
            k: v / total for k, v in cfg.actions_distribution.items()
        }

        # Normalizar/limpar tags
        cfg.tags = [t.strip() for t in cfg.tags if isinstance(t, str) and t.strip()]

        _cfg_singleton = cfg
    return _cfg_singleton
