from typing import Tuple, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.interacoes import tentar_dar_like, tentar_follow, tentar_comentar, tentar_visualizar_stories
from utils.logger import espera_humana
from utils.settings import NAVIGATE_MIN, NAVIGATE_MAX, WAIT_PAGE

def _abrir_link(driver, link: Optional[str]) -> bool:
    if not link: return True
    try:
        driver.get(link)
        WebDriverWait(driver, WAIT_PAGE).until(EC.presence_of_element_located((By.XPATH,"//article | //div[contains(@role,'dialog')]//article | //video | //img")))
        espera_humana(NAVIGATE_MIN, NAVIGATE_MAX); return True
    except Exception:
        return False

def do_like(driver, link: Optional[str]) -> Tuple[bool, str]:
    if not _abrir_link(driver, link): return False, str(link or "")
    return tentar_dar_like(driver), str(link or "")

def do_follow(driver, link: Optional[str]) -> Tuple[bool, str]:
    if not _abrir_link(driver, link): return False, str(link or "")
    return tentar_follow(driver), str(link or "")

def do_comentario(driver, link: Optional[str]) -> Tuple[bool, str]:
    if not _abrir_link(driver, link): return False, str(link or "")
    return tentar_comentar(driver), str(link or "")

def do_stories(driver) -> Tuple[bool, str]:
    return tentar_visualizar_stories(driver), "stories"

def realizar_acao(driver, acao: str, link: Optional[str] = None):
    if acao == "like": return do_like(driver, link)
    if acao == "follow": return do_follow(driver, link)
    if acao == "comentario": return do_comentario(driver, link)
    if acao == "stories": return do_stories(driver)
    return False, str(link or "")
