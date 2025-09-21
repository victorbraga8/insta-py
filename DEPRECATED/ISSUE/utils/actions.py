import os, time, random
from pathlib import Path
from typing import List, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def _ms(n: int):
    time.sleep(n / 1000.0)


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

DEBUG_VISUAL = os.getenv("DEBUG_VISUAL", "false").lower() == "true"
DEBUG_MS = int(os.getenv("DEBUG_MS", "1200"))


def _dbg_mark(driver, el, label: str):
    if not DEBUG_VISUAL or el is None:
        return
    try:
        driver.execute_script(
            """
        (function(el,label,ms){
          try{
            var r=el.getBoundingClientRect();
            var o=document.createElement('div');
            o.style.position='fixed';
            o.style.left=(r.left-2)+'px';
            o.style.top=(r.top-2)+'px';
            o.style.width=(r.width+4)+'px';
            o.style.height=(r.height+4)+'px';
            o.style.border='2px solid #00e5ff';
            o.style.boxShadow='0 0 8px rgba(0,229,255,0.8)';
            o.style.zIndex='2147483647';
            o.style.pointerEvents='none';
            o.style.borderRadius='6px';
            var b=document.createElement('div');
            b.textContent=label||'';
            b.style.position='fixed';
            b.style.left=(r.left)+'px';
            b.style.top=(r.top-24)+'px';
            b.style.padding='2px 6px';
            b.style.background='rgba(0,229,255,0.9)';
            b.style.color='#000';
            b.style.font='12px/1.2 monospace';
            b.style.borderRadius='6px';
            b.style.zIndex='2147483647';
            b.style.pointerEvents='none';
            document.body.appendChild(o);
            document.body.appendChild(b);
            setTimeout(function(){try{o.remove();b.remove();}catch(e){}}, ms||1200);
          }catch(e){}
        })(arguments[0], arguments[1], arguments[2]);
        """,
            el,
            label,
            DEBUG_MS,
        )
    except Exception:
        pass


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


def settle_page(driver, min_wait_ms: int = 3000, max_wait_ms: int = 4500):
    try:
        try:
            art = driver.find_element(
                By.XPATH, "((//div[@role='dialog']//article) | //article)[1]"
            )
        except Exception:
            art = None
        target = art if art else driver.find_element(By.TAG_NAME, "body")
        driver.execute_script(
            """
            try{ window.focus(); }catch(e){}
            try{ if (document && document.body) document.body.focus(); }catch(e){}
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


LIKE_XPATHS = [
    "( ((//div[@role='dialog']//article) | //article)"
    "  //button[.//*[name()='svg' and contains(translate(@aria-label,'LIKECURTIR','likecurtir'),'like')]] )[1]",
    "( ((//div[@role='dialog']//article) | //article)"
    "  //*[name()='svg' and contains(translate(@aria-label,'LIKECURTIR','likecurtir'),'like')"
    "     and not(ancestor::ul) and not(ancestor::li)] )[1]",
]

UNLIKE_XPATHS = [
    "( ((//div[@role='dialog']//article) | //article)"
    "  //button[.//*[name()='svg' and contains(translate(@aria-label,'UNLIKEDESCURTIR','unlikedescurtir'),'unlike')]] )[1]",
    "( ((//div[@role='dialog']//article) | //article)"
    "  //*[name()='svg' and contains(translate(@aria-label,'UNLIKEDESCURTIR','unlikedescurtir'),'unlike')] )[1]",
]

DEBUG_VISUAL = os.getenv("DEBUG_VISUAL", "false").lower() == "true"
DEBUG_MS = int(os.getenv("DEBUG_MS", "1200"))


def _dbg_mark(driver, el, label: str):
    if not DEBUG_VISUAL or el is None:
        return
    try:
        driver.execute_script(
            """
        (function(el,label,ms){
          try{
            var r=el.getBoundingClientRect();
            var box=document.createElement('div');
            box.style.position='fixed';
            box.style.left=(r.left-2)+'px';
            box.style.top=(r.top-2)+'px';
            box.style.width=(r.width+4)+'px';
            box.style.height=(r.height+4)+'px';
            box.style.border='2px solid #00e5ff';
            box.style.boxShadow='0 0 8px rgba(0,229,255,0.8)';
            box.style.borderRadius='6px';
            box.style.zIndex='2147483647';
            box.style.pointerEvents='none';

            var tag=document.createElement('div');
            tag.textContent=label||'';
            tag.style.position='fixed';
            tag.style.left=(r.left)+'px';
            tag.style.top=(r.top-24)+'px';
            tag.style.padding='2px 6px';
            tag.style.background='rgba(0,229,255,0.9)';
            tag.style.color='#000';
            tag.style.font='12px/1.2 monospace';
            tag.style.borderRadius='6px';
            tag.style.zIndex='2147483647';
            tag.style.pointerEvents='none';

            document.body.appendChild(box);
            document.body.appendChild(tag);
            setTimeout(function(){try{box.remove();tag.remove();}catch(e){}}, ms||1200);
          }catch(e){}
        })(arguments[0], arguments[1], arguments[2]);
        """,
            el,
            label,
            DEBUG_MS,
        )
    except Exception:
        pass


# --- substitua a função like_post por esta ---
def like_post(driver) -> bool:
    """Tenta curtir o post atual. Tolera variações de UI/idioma. Mostra debug visual."""
    try:
        # 1) já curtido?
        liked_locators = [
            (By.CSS_SELECTOR, "svg[aria-label='Descurtir']"),
            (By.CSS_SELECTOR, "svg[aria-label='Unlike']"),
            (
                By.XPATH,
                "((//div[@role='dialog']//article) | //article)//button//*[name()='svg' and (@aria-label='Descurtir' or @aria-label='Unlike')]",
            ),
        ]
        for by, sel in liked_locators:
            els = driver.find_elements(by, sel)
            if els:
                _dbg_mark(driver, els[0], "ALREADY LIKED")
                return True

        # 2) botões de like possíveis (absorvendo seus seletores + variações)
        click_locators = [
            (By.CSS_SELECTOR, "span > button[aria-label*='Curtir']"),
            (By.CSS_SELECTOR, "span > button[aria-label*='Like']"),
            (
                By.XPATH,
                "//section//button//*[name()='svg' and (@aria-label='Curtir' or @aria-label='Like')]/..",
            ),
            (
                By.XPATH,
                "//div[@role='dialog']//button//*[name()='svg' and (@aria-label='Curtir' or @aria-label='Like')]/..",
            ),
            (
                By.XPATH,
                "(((//div[@role='dialog']//article) | //article)//*[name()='svg' and contains(translate(@aria-label,'LIKECURTIR','likecurtir'),'like')])[1]/ancestor::button[1]",
            ),
        ]

        for by, sel in click_locators:
            try:
                el = _visible_click(driver, by, sel, 6)  # já centraliza e tenta clicar
                _dbg_mark(driver, el, "LIKE")
                _ms(random.randint(140, 260))

                # valida mudança para 'Descurtir'
                for _ in range(10):
                    liked = driver.find_elements(
                        By.CSS_SELECTOR,
                        "svg[aria-label='Descurtir'], svg[aria-label='Unlike']",
                    )
                    if liked:
                        _dbg_mark(driver, liked[0], "LIKED")
                        return True
                    _ms(120)
            except Exception:
                continue

        return False
    except Exception:
        return False


def open_comment_box(driver):
    triggers = [
        "(//button[@aria-label='Comentar' or @aria-label='Comment'])[1]",
        "(//svg[@aria-label='Comentar' or @aria-label='Comment']/ancestor::button)[1]",
    ]
    for xp in triggers:
        els = driver.find_elements(By.XPATH, xp)
        if els:
            try:
                _center(driver, els[0])
                _hover(driver, els[0])
                els[0].click()
                _ms(120)
                break
            except Exception:
                pass
    fields = [
        "((//div[@role='dialog']//form) | //form)//textarea[1]",
        "((//div[@role='dialog']//form) | //form)//div[@contenteditable='true'][1]",
    ]
    for xp in fields:
        els = driver.find_elements(By.XPATH, xp)
        if els:
            try:
                _center(driver, els[0])
                _hover(driver, els[0])
                els[0].click()
                _ms(80)
                return els[0]
            except Exception:
                pass
    return None


def _type_human_text(
    driver, el, text: str, lo: int, hi: int, err: float, post_pause: int
):
    """Digita como humano em textarea OU contenteditable usando send_keys."""
    _ms(random.randint(COMMENT_FOCUS_HOLD_MS, COMMENT_FOCUS_HOLD_MS + 400))

    try:
        ActionChains(driver).move_to_element(el).pause(0.05).click().perform()
        driver.execute_script("arguments[0].focus && arguments[0].focus();", el)
    except Exception:
        pass

    tag = (el.tag_name or "").lower()
    is_textarea = tag == "textarea"

    # Limpa campo
    try:
        if is_textarea:
            el.clear()
        el.send_keys(Keys.CONTROL, "a")
        el.send_keys(Keys.BACKSPACE)
    except Exception:
        pass

    # Digita char a char
    for ch in text:
        el.send_keys(ch)
        if random.random() < err:
            el.send_keys(Keys.BACKSPACE)
            _ms(random.randint(lo, hi))
            el.send_keys(ch)
        _ms(random.randint(lo, hi))

    # Notifica mudança
    try:
        driver.execute_script(
            "try{arguments[0].dispatchEvent(new Event('input',{bubbles:true}))}catch(e){}",
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
        box = open_comment_box(driver)
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
            form = box.find_element(By.XPATH, "ancestor::form[1]")
        except Exception:
            form = None
        if form:
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
                box.send_keys(Keys.ENTER)
                sent = True
            except Exception:
                pass
        _ms(random.randint(700, 1300))
        return True if sent else False
    except Exception:
        return False


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
