import random
from collections import deque
from typing import Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.logger import log, espera_humana
from utils.settings import WAIT_CLICK, TYPING_MIN, TYPING_MAX

def _visible_click(driver, by, sel):
    el = WebDriverWait(driver, WAIT_CLICK).until(EC.element_to_be_clickable((by, sel)))
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    return el

def _pick(driver, locators):
    last_err = None
    for by, sel in locators:
        try:
            return WebDriverWait(driver, WAIT_CLICK).until(EC.presence_of_element_located((by, sel)))
        except Exception as e:
            last_err = e
    raise last_err if last_err else Exception("element not found")

# comentarios sem repetição
try:
    with open("comentarios.txt","r",encoding="utf-8") as f:
        _comentarios = [l.strip() for l in f if l.strip()]
except FileNotFoundError:
    _comentarios = []
random.shuffle(_comentarios)
_comentarios_queue = deque(_comentarios)

def _proximo_comentario()->Optional[str]:
    if not _comentarios_queue: return None
    return _comentarios_queue.popleft()

def tentar_dar_like(driver)->bool:
    try:
        # já curtido?
        liked_locators = [
            (By.CSS_SELECTOR, "svg[aria-label='Descurtir']"),
            (By.CSS_SELECTOR, "svg[aria-label='Unlike']"),
            (By.XPATH, "//button//*[name()='svg' and (@aria-label='Descurtir' or @aria-label='Unlike')]"),
        ]
        for by, sel in liked_locators:
            if driver.find_elements(by, sel):
                return True
        # botões de like possíveis
        click_locators = [
            (By.CSS_SELECTOR, "span > button[aria-label*='Curtir']"),
            (By.CSS_SELECTOR, "span > button[aria-label*='Like']"),
            (By.XPATH, "//section//button//*[name()='svg' and (@aria-label='Curtir' or @aria-label='Like')]/.."),
            (By.XPATH, "//div[@role='dialog']//button//*[name()='svg' and (@aria-label='Curtir' or @aria-label='Like')]/.."),
        ]
        for by, sel in click_locators:
            try:
                _visible_click(driver, by, sel); espera_humana(); return True
            except Exception:
                continue
        raise Exception("like button not found")
    except Exception as e:
        log(f"[LIKE ERRO] {str(e).splitlines()[0]}")
        return False

def tentar_follow(driver)->bool:
    try:
        already = [
            (By.XPATH, "//button[.='Seguindo' or .='Following' or contains(.,'Solicitado') or contains(.,'Requested')]"),
        ]
        for by, sel in already:
            if driver.find_elements(by, sel): return True
        clickers = [
            (By.XPATH, "//header//button[.='Seguir' or .='Follow']"),
            (By.XPATH, "//button[.='Seguir' or .='Follow']"),
            (By.XPATH, "//div[@role='dialog']//button[.='Seguir' or .='Follow']"),
        ]
        for by, sel in clickers:
            try:
                _visible_click(driver, by, sel); espera_humana(); return True
            except Exception:
                continue
        raise Exception("follow button not found")
    except Exception as e:
        log(f"[FOLLOW ERRO] {str(e).splitlines()[0]}")
        return False

def tentar_comentar(driver)->bool:
    try:
        comentario = _proximo_comentario()
        if not comentario:
            log("[COMENTARIO ERRO] sem comentários disponíveis"); return False
        caixa_loc = [
            (By.XPATH, "//form//textarea[not(@disabled)]"),
            (By.CSS_SELECTOR, "form textarea[aria-label]"),
            (By.XPATH, "//textarea[@aria-label and not(@disabled)]"),
        ]
        caixa = _pick(driver, caixa_loc)
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", caixa)
        ActionChains(driver).move_to_element(caixa).click().perform()
        for ch in comentario:
            caixa.send_keys(ch)
            espera_humana(TYPING_MIN, TYPING_MAX)
        bts = [
            (By.XPATH, "//form//button[@type='submit']"),
            (By.XPATH, "//form//button[.='Publicar' or .='Post']"),
        ]
        try:
            _visible_click(driver, *bts[0])
        except Exception:
            _visible_click(driver, *bts[1])
        espera_humana()
        log(f"Comentario enviado: {comentario}")
        return True
    except Exception as e:
        log(f"[COMENTARIO ERRO] {str(e).splitlines()[0]}")
        return False

def tentar_visualizar_stories(driver)->bool:
    try:
        # assume já na home por do_stories; se não, tenta ir
        driver.get("https://www.instagram.com/")
        _ = WebDriverWait(driver, 12).until(EC.presence_of_element_located((By.TAG_NAME, "nav")))
        # clica no primeiro anel
        try:
            _visible_click(driver, By.XPATH, "(//div[contains(@aria-label,'Stories') or @role='link']//canvas/ancestor::button | //div[@role='button']//canvas/..)[1]")
        except Exception:
            pass
        WebDriverWait(driver, 10).until(EC.presence_of_all_elements_located((By.TAG_NAME, "canvas")))
        espera_humana()
        return True
    except Exception as e:
        log(f"[STORIES ERRO] {str(e).splitlines()[0]}")
        return False
