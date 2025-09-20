import os, time, random
from pathlib import Path
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _ms(n):
    time.sleep(n / 1000.0)


# Delays padrão (o runner pode enviar outros via params nos métodos)
NAV_MIN = int(os.getenv("NAVIGATE_MIN_MS", "700"))
NAV_MAX = int(os.getenv("NAVIGATE_MAX_MS", "1500"))
ACT_MIN = int(os.getenv("ACTION_AFTER_MIN_MS", "800"))
ACT_MAX = int(os.getenv("ACTION_AFTER_MAX_MS", "1600"))

TYPE_MIN_DEF = int(os.getenv("TYPE_MIN_MS", "45"))
TYPE_MAX_DEF = int(os.getenv("TYPE_MAX_MS", "120"))
TYPE_ERR_DEF = float(os.getenv("TYPE_MISTAKE_PROB", "0.02"))
POST_TYPE_PAUSE_DEF = int(os.getenv("POST_TYPE_PAUSE_MS", "350"))

COMMENT_FOCUS_HOLD_MS = int(os.getenv("COMMENT_FOCUS_HOLD_MS", "900"))
COMMENT_BEFORE_SEND_MS = int(os.getenv("COMMENT_BEFORE_SEND_MS", "450"))

# ---------------- helpers ----------------


def _hover(driver, el, lo=120, hi=320):
    try:
        ActionChains(driver).move_to_element(el).pause(
            random.uniform(lo / 1000, hi / 1000)
        ).perform()
    except Exception:
        pass


def _center(driver, el):
    try:
        driver.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
        _ms(random.randint(180, 360))
    except Exception:
        pass


def _visible_click(driver, by, sel, t=8):
    el = WebDriverWait(driver, t).until(EC.element_to_be_clickable((by, sel)))
    _center(driver, el)
    _hover(driver, el)
    try:
        el.click()
    except Exception:
        driver.execute_script("arguments[0].click();", el)
    return el


def _svg_title_text(svg_el) -> str:
    try:
        t = svg_el.find_element(By.TAG_NAME, "title")
        return (t.text or "").strip()
    except Exception:
        return ""


# ---------------- settle: clicar no DOM após navegar ----------------


def settle_page(driver, min_wait_ms: int = 3000, max_wait_ms: int = 4500):
    """
    Após driver.get/navegação:
      - clica dentro da DOM (centro do <article> ou, fallback, <body>)
      - aguarda 3.0–4.5s (configurável) para “assentar” a página
    """
    try:
        # tenta focar o article do post (modal ou feed)
        try:
            art = driver.find_element(
                By.XPATH, "((//div[@role='dialog']//article) | //article)[1]"
            )
        except Exception:
            art = None

        target = art if art else driver.find_element(By.TAG_NAME, "body")

        driver.execute_script(
            """
            const el = arguments[0];
            try { el.scrollIntoView({block:'center'}); } catch(e) {}
            const r = el.getBoundingClientRect();
            const x = Math.floor(r.left + r.width/2);
            const y = Math.floor(r.top + r.height/2);
            const node = document.elementFromPoint(x, y) || el;
            node.dispatchEvent(new MouseEvent('mousemove', {bubbles:true, clientX:x, clientY:y}));
            node.dispatchEvent(new MouseEvent('mousedown', {bubbles:true, clientX:x, clientY:y}));
            node.dispatchEvent(new MouseEvent('mouseup',   {bubbles:true, clientX:x, clientY:y}));
            node.dispatchEvent(new MouseEvent('click',     {bubbles:true, clientX:x, clientY:y}));
        """,
            target,
        )
    except Exception:
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            ActionChains(driver).move_to_element_with_offset(
                body, 30, 30
            ).click().perform()
        except Exception:
            pass

    _ms(random.randint(min_wait_ms, max_wait_ms))


# ---------------- LIKE ----------------

# “Descurtir” 24x24 (já curtido)
_UNLIKE_XP = (
    "((//div[@role='dialog']//article) | //article)"
    "//*[name()='svg' and (@aria-label='Descurtir' or @aria-label='Unlike')"
    " and @width='24' and @height='24' and not(ancestor::ul) and not(ancestor::li)]"
)

# “Curtir/Like” 24x24 no post (fora de listas/comentários)
_LIKE_SVG_XP = (
    "( ((//div[@role='dialog']//article) | //article)"
    "  //*[name()='svg' and (@aria-label='Curtir' or @aria-label='Like')"
    "     and @width='24' and @height='24' and not(ancestor::ul) and not(ancestor::li)] )[1]"
)


def _find_like_svg(driver):
    els = driver.find_elements(By.XPATH, _LIKE_SVG_XP)
    return els[0] if els else None


def _find_like_clickable_from_svg(svg_el):
    try:
        btns = svg_el.find_elements(
            By.XPATH, "./ancestor::*[@role='button' or self::button][1]"
        )
        return btns[0] if btns else None
    except Exception:
        return None


def _is_liked(driver) -> bool:
    try:
        return len(driver.find_elements(By.XPATH, _UNLIKE_XP)) > 0
    except Exception:
        return False


def like_post(driver) -> bool:
    try:
        # se já está curtido, ok
        if _is_liked(driver):
            return True

        for _ in range(3):
            svg = _find_like_svg(driver)
            if not svg:
                _ms(220)
                continue

            # alguns builds não trazem <title>, então aceitar vazio também é ok
            title_txt = _svg_title_text(svg).lower()
            if not any(k in title_txt for k in ("curtir", "like", "")):
                _ms(120)
                continue

            click_el = _find_like_clickable_from_svg(svg)
            if not click_el:
                _ms(120)
                continue

            _center(driver, click_el)
            _hover(driver, click_el)
            try:
                WebDriverWait(driver, 5).until(EC.element_to_be_clickable(click_el))
            except Exception:
                pass

            try:
                click_el.click()
            except Exception:
                try:
                    driver.execute_script("arguments[0].click();", click_el)
                except Exception:
                    pass

            # valida troca para “Descurtir”
            for _ in range(10):
                if _is_liked(driver):
                    return True
                _ms(120)

            _ms(random.randint(180, 320))

        return False
    except Exception:
        return False


# ---------------- COMMENT ----------------


def open_comment_box(driver):
    try:
        locs = [
            (
                By.XPATH,
                "(//svg[@aria-label='Comentar' or @aria-label='Comment']/ancestor::button)[1]",
            ),
            (By.XPATH, "//button[@aria-label='Comentar' or @aria-label='Comment']"),
        ]
        for by, sel in locs:
            try:
                _visible_click(driver, by, sel, 6)
                _ms(random.randint(200, 500))
                return
            except Exception:
                continue
    except Exception:
        pass


def _find_comment_form(driver):
    xp = "((//div[@role='dialog']//article) | //article)//form[.//textarea or .//*[@role='textbox']][1]"
    try:
        els = driver.find_elements(By.XPATH, xp)
        return els[0] if els else None
    except Exception:
        return None


def _find_textbox_in_form(form):
    try:
        els = form.find_elements(
            By.XPATH, ".//textarea[@aria-label or @placeholder] | .//*[@role='textbox']"
        )
        return els[0] if els else None
    except Exception:
        return None


def _type_human_text(
    driver, el, text: str, lo: int, hi: int, err: float, post_pause: int
):
    _ms(random.randint(COMMENT_FOCUS_HOLD_MS, COMMENT_FOCUS_HOLD_MS + 400))

    tag = (el.tag_name or "").lower()
    is_textarea = tag == "textarea"
    is_ce = False
    try:
        is_ce = (
            el.get_attribute("contenteditable") == "true"
            or el.get_attribute("role") == "textbox"
        )
    except Exception:
        pass

    if is_textarea:
        try:
            el.clear()
        except Exception:
            pass
        try:
            driver.execute_script("try{arguments[0].value='';}catch(e){}", el)
        except Exception:
            pass

    for ch in text:
        if is_ce:
            try:
                driver.execute_script(
                    "document.execCommand('insertText', false, arguments[0]);", ch
                )
            except Exception:
                cur = (el.get_attribute("textContent") or "") + ch
                driver.execute_script(
                    "arguments[0].textContent = arguments[1];", el, cur
                )
        else:
            el.send_keys(ch)
        if random.random() < err and not is_ce:
            el.send_keys(Keys.BACKSPACE)
            _ms(random.randint(lo, hi))
            el.send_keys(ch)
        _ms(random.randint(lo, hi))

    try:
        driver.execute_script(
            "try{arguments[0].dispatchEvent(new Event('input',{bubbles:true}));}catch(e){}",
            el,
        )
    except Exception:
        pass

    _ms(post_pause)


def comment_post(
    driver,
    text: str,
    lo: int = TYPE_MIN_DEF,
    hi: int = TYPE_MAX_DEF,
    err: float = TYPE_ERR_DEF,
    post_pause: int = POST_TYPE_PAUSE_DEF,
) -> bool:
    try:
        open_comment_box(driver)
        form = _find_comment_form(driver)
        if not form:
            return False
        box = _find_textbox_in_form(form)
        if not box:
            return False

        _center(driver, box)
        _hover(driver, box)
        try:
            ActionChains(driver).move_to_element(box).pause(0.05).click().perform()
            driver.execute_script("arguments[0].focus && arguments[0].focus();", box)
        except Exception:
            pass

        _type_human_text(driver, box, text, lo, hi, err, post_pause)

        _ms(random.randint(COMMENT_BEFORE_SEND_MS, COMMENT_BEFORE_SEND_MS + 400))

        sent = False
        try:
            btns = form.find_elements(
                By.XPATH, ".//button[@type='submit' or .='Post' or .='Publicar']"
            )
            if btns:
                _center(driver, btns[0])
                _hover(driver, btns[0])
                if not btns[0].is_enabled():
                    _ms(120)
                btns[0].click()
                sent = True
        except Exception:
            pass

        if not sent:
            try:
                box.send_keys(Keys.ENTER)  # ENTER no textbox, nunca global
                sent = True
            except Exception:
                pass

        _ms(random.randint(700, 1300))
        return True if sent else False
    except Exception:
        return False


# ---------------- POOL (comentários recentes) ----------------


def load_comments_pool(path: str, recent_path: str, recent_limit: int) -> List[str]:
    p = Path(path)
    if not p.exists():
        return []
    pool = [
        ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()
    ]
    rp = Path(recent_path)
    recent = []
    if rp.exists():
        recent = [
            ln.strip()
            for ln in rp.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    cand = [c for c in pool if c not in set(recent)]
    random.shuffle(cand)
    if not cand:
        cand = pool[:]
    random.shuffle(cand)
    return cand


def mark_comment_used(recent_path: str, text: str, recent_limit: int):
    rp = Path(recent_path)
    lines = []
    if rp.exists():
        lines = [
            ln.strip()
            for ln in rp.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
    lines.append(text)
    lines = lines[-recent_limit:]
    rp.parent.mkdir(parents=True, exist_ok=True)
    rp.write_text("\n".join(lines), encoding="utf-8")
