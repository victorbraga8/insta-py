import random, time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException, StaleElementReferenceException

LOGIN_URL = "https://www.instagram.com/accounts/login/?next=/"

def _dismiss(driver):
    try:
        btn = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Permitir todos'] | //button[normalize-space()='Accept'] | //button[contains(., 'Aceitar')] | //button[contains(., 'Allow all')] | //button[contains(., 'Only allow essential')]")))
        btn.click()
        time.sleep(0.6 + random.random())
    except Exception:
        pass

def _type_slow(el, text: str):
    try:
        el.clear()
    except Exception:
        pass
    for ch in text:
        el.send_keys(ch)
        time.sleep(0.03 + random.random() * 0.07)

def realizar_login(driver, user: str, pwd: str, timeout: int = 20) -> bool:
    driver.get(LOGIN_URL)
    _dismiss(driver)
    try:
        WebDriverWait(driver, timeout).until(EC.presence_of_element_located((By.NAME, "username")))
    except TimeoutException:
        driver.get(LOGIN_URL)
    try:
        u = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.NAME, "username")))
        p = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.NAME, "password")))
        ActionChains(driver).move_to_element(u).click().perform()
        _type_slow(u, user)
        ActionChains(driver).move_to_element(p).click().perform()
        _type_slow(p, pwd)
        enter = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.XPATH, "//form//button[@type='submit']")))
        enter.click()
    except (TimeoutException, ElementClickInterceptedException, StaleElementReferenceException):
        return False
    try:
        WebDriverWait(driver, 25).until(EC.presence_of_element_located((By.XPATH, "//nav//a[contains(@href,'/explore/')] | //a[contains(@href,'/accounts/edit')] | //div[@role='menu']")))
        return True
    except TimeoutException:
        try:
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.XPATH, "//*[contains(., 'confirmar')] | //*[contains(., 'Verificar')] | //*[contains(., 'Checkpoint')]")))
            return False
        except TimeoutException:
            return False
