# utils/logger.py
# Logger com saída colorida no terminal + arquivo rotativo por perfil.

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

# --- Cores ANSI para console ---
RESET = "\033[0m"
COLORS = {
    "DEBUG": "\033[38;5;244m",  # cinza
    "INFO": "\033[38;5;39m",  # azul
    "WARNING": "\033[38;5;214m",  # laranja
    "ERROR": "\033[38;5;203m",  # vermelho
    "CRITICAL": "\033[1;41m",  # fundo vermelho
}


class ColorFormatter(logging.Formatter):
    def __init__(self, fmt: str, datefmt: Optional[str] = None):
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        levelname = record.levelname
        color = COLORS.get(levelname, "")
        record.levelname = f"{color}{levelname}{RESET}" if color else levelname
        return super().format(record)


def _to_level(level_str: str) -> int:
    level_str = (level_str or "INFO").upper()
    return {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARN,
        "WARNING": logging.WARN,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }.get(level_str, logging.INFO)


def get_logger(
    profile_id: str, level: str = "INFO", file_path: str = "logs/insta_py.log"
) -> logging.Logger:
    """
    Cria (ou reaproveita) um logger por perfil com:
      - Console colorido
      - Arquivo rotativo UTF-8 (5MB, 3 backups)
      - Formatação consistente: timestamp | nível | perfil | thread | mensagem
    """
    logger_name = f"insta_py.{profile_id}"
    logger = logging.getLogger(logger_name)
    logger.setLevel(_to_level(level))
    logger.propagate = False  # evita duplicação no root

    # Evita adicionar handlers duplicados se já existir
    if logger.handlers:
        # ainda assim atualiza nível dos handlers existentes
        for h in logger.handlers:
            h.setLevel(_to_level(level))
        return logger

    # --- Formatos ---
    datefmt = "%Y-%m-%d %H:%M:%S"
    base_fmt = "%(asctime)s | %(levelname)s | %(name)s | %(threadName)s | %(message)s"
    color_fmt = ColorFormatter(base_fmt, datefmt=datefmt)
    file_fmt = logging.Formatter(base_fmt, datefmt=datefmt)

    # --- Console handler (colorido) ---
    ch = logging.StreamHandler(stream=sys.stdout)
    ch.setLevel(_to_level(level))
    ch.setFormatter(color_fmt)
    logger.addHandler(ch)

    # --- File handler (rotativo) ---
    try:
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            filename=str(log_path),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
            encoding="utf-8",
        )
        fh.setLevel(_to_level(level))
        fh.setFormatter(file_fmt)
        logger.addHandler(fh)
    except Exception:
        # Se der erro ao criar arquivo, segue só com console
        logger.warning(
            "Não foi possível inicializar arquivo de log. Seguindo apenas com console."
        )

    # Primeira linha para identificar o perfil no início
    logger.info(f"Logger pronto para perfil={profile_id}")
    return logger
