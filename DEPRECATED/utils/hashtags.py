import time, random
from urllib.parse import urljoin
from typing import List
from selenium.webdriver.common.by import By
from utils.settings import SCROLL_STEPS, SCROLL_MAX, SCROLL_MIN
def _scroll(driver, steps=SCROLL_STEPS, pausa=(SCROLL_MIN, SCROLL_MAX)):
    last = 0
    for _ in range(steps):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(random.uniform(*pausa))
        cur = driver.execute_script("return document.body.scrollHeight;")
        if cur == last: break; last = cur
def coletar_links_hashtag(driver, hashtag: str, limite: int = 80) -> List[str]:
    base = "https://www.instagram.com"
    driver.get(f"{base}/explore/tags/{hashtag}/"); time.sleep(random.uniform(2.5,4.0))
    _scroll(driver)
    cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/p/'], a[href*='/reel/']")
    hrefs = []
    for c in cards:
        href = c.get_attribute("href")
        if href:
            if href.startswith('/'): href = urljoin(base, href)
            hrefs.append(href)
        if len(hrefs) >= limite: break
    return list(dict.fromkeys(hrefs))[:limite]
