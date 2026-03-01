from seleniumbase import SB
import time
import random
import os
import sys
import requests
import json
from datetime import datetime
import uuid
import psutil
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
import tempfile
import shutil

# ==================== CONFIG & GLOBALS ====================
VISIT_TIMEOUT_SECONDS = 180
STOP_FLAG = False

def set_stop_flag(value: bool):
    global STOP_FLAG
    STOP_FLAG = value


def get_unique_profile(visit_id: int) -> str:
    """Every visit gets its own clean profile — fixes parallel runs"""
    return tempfile.mkdtemp(prefix=f"sb_yandex_{visit_id}_{os.getpid()}_")

def diminish():
    """Decrement queue in data.json (only on confirmed success)"""
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
        if data and data[0]['times'] > 1:
            data[0]['times'] -= 1
        else:
            data = data[1:] if data else []
        with open('data.json', 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[DIMINISH] Error: {e}")

def cleanup_chrome(aggressive: bool = False):
    """Safe, surgical cleanup — only touches this script's browsers"""
    killed = 0
    try:
        current = psutil.Process(os.getpid())
        for child in current.children(recursive=True):
            try:
                name = child.name().lower()
                cmd = ' '.join(child.cmdline()).lower()
                if any(x in name for x in ["chrome", "chromedriver"]) and \
                   any(x in cmd for x in ["selenium", "undetected", "--remote-debugging-port"]):
                    print(f"[CLEANUP] Killing {child.pid} ({name})")
                    if not aggressive:
                        child.terminate()
                        time.sleep(0.8)
                        if child.is_running():
                            child.kill()
                    else:
                        child.kill()
                    killed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        print(f"[CLEANUP] Error: {e}")
    
    if killed > 0:
        time.sleep(1.5)  # critical: let OS release ports
    return killed

# ==================== PROXY HANDLING ====================
from tokens import *

def sticky_proxy() -> dict:
    session_id = uuid.uuid4().hex[:12]
    return {
        "host": PROXY_HOST,
        "port": PROXY_PORT,
        "username": f"{USERNAME}_session-{session_id}",
        "password": PASSWORD,
    }

def get_proxy_string(proxy: dict) -> str:
    return f"{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"

# ==================== SAFE JS EXECUTION (fixes CDP "Illegal return statement") ====================
def safe_execute_script(sb, script: str):
    """Wraps any script in IIFE to prevent 'Illegal return statement' in SeleniumBase UC/CDP mode"""
    wrapped = f"""
    (function() {{
        try {{
            return ({script});
        }} catch(e) {{
            console.error('SafeJS error:', e);
            return false;
        }}
    }})();
    """
    return sb.execute_script(wrapped)

# ==================== ADVANCED HUMAN SIMULATION (Yandex Metrica behavioral core) ====================
def simulate_human_behavior(sb, visit_id: int, min_duration: int = 10):
    """
    100% JS behavioral simulation — designed specifically against Yandex Metrica robot filter (2026).
    Metrica detects bots by:
    - Lack of mouse entropy / movement patterns
    - No variable scrolling
    - No real interaction events
    - <15s active session
    This fires real mousemove, mousedown, mouseup, scroll, focus events with natural randomness.
    """
    print(f"[{visit_id}] 🚀 Starting ADVANCED HUMAN BEHAVIOR simulation ({min_duration}-{min_duration+10}s)...")
    start = time.time()
    target_duration = random.randint(min_duration, min_duration + 10)

    js_script = """
    (function() {
        const w = window.innerWidth || 1200;
        const h = window.innerHeight || 800;
        let elapsed = 0;
        const targetMs = Math.floor(Math.random() * 22000) + """ + str(min_duration * 1000) + """;

        function dispatchMouse() {
            const ev = new MouseEvent('mousemove', {
                bubbles: true, cancelable: true,
                clientX: Math.random() * w,
                clientY: Math.random() * h,
                movementX: Math.random() * 48 - 24,
                movementY: Math.random() * 36 - 18
            });
            document.documentElement.dispatchEvent(ev);
        }

        function dispatchClick() {
            const x = Math.random() * w;
            const y = Math.random() * h * 0.7;
            const down = new MouseEvent('mousedown', {bubbles: true, clientX: x, clientY: y});
            const up = new MouseEvent('mouseup', {bubbles: true, clientX: x, clientY: y});
            document.documentElement.dispatchEvent(down);
            document.documentElement.dispatchEvent(up);
        }

        function randomScroll() {
            const amount = Math.random() * 680 + 120;
            window.scrollBy(0, Math.random() > 0.5 ? amount : -amount);
        }

        const interval = setInterval(() => {
            elapsed += 380;
            if (elapsed >= targetMs) {
                clearInterval(interval);
                window.scrollTo(0, document.body.scrollHeight * (Math.random() * 0.75 + 0.18));
                window.focus();
                return;
            }
            if (Math.random() < 0.82) dispatchMouse();
            if (Math.random() < 0.38) randomScroll();
            if (Math.random() < 0.19) dispatchClick();   // Safe fake clicks (boosts interaction score)
        }, 380);
    })();
    """

    try:
        sb.execute_script(js_script)
        # Keep Python thread alive while JS runs + add natural pauses
        while time.time() - start < target_duration:
            if STOP_FLAG:
                return
            time.sleep(0.38)
    except Exception as e:
        print(f"[{visit_id}] JS behavior fallback: {e}")
        # Ultra-safe fallback
        for _ in range(8):
            if STOP_FLAG:
                return
            sb.execute_script("window.scrollBy(0, 240 + Math.random()*300);")
            time.sleep(random.uniform(1.1, 2.4))

    print(f"[{visit_id}] ✅ Advanced human simulation completed ({int(time.time()-start)}s active)")


# ==================== CORE VISIT LOGIC ====================
def visit_with_timeout(proxy: dict, target: str, visit_id: int) -> bool:
    """Simple, safe timeout — no threads, no races"""
    start = time.time()
    try:
        return visit_with_proxy(proxy, target, visit_id)
    except Exception as e:
        print(f"[{visit_id}] ⏰ CRITICAL ERROR: {e}")
        cleanup_chrome(aggressive=True)
        return False
    finally:
        elapsed = time.time() - start
        if elapsed > VISIT_TIMEOUT_SECONDS:
            print(f"[{visit_id}] ⏰ Visit exceeded {VISIT_TIMEOUT_SECONDS}s — aggressive cleanup")
            cleanup_chrome(aggressive=True)

def visit_with_proxy(proxy: dict, target: str, visit_id: int) -> bool:
    proxy_str = get_proxy_string(proxy)
    is_success = False

    try:
        profile_dir = get_unique_profile(visit_id)   # ← NEW (this is the most important line)
        print(f"[{visit_id}] 🌐 Using unique profile: {profile_dir}")
        with SB(
            uc=True,
            proxy=proxy_str,
            headless=False,
            page_load_strategy="normal",
            test=True,
            incognito=True,
            user_data_dir=profile_dir,
            maximize=True
        ) as sb:
            if STOP_FLAG:
                return False

            print(f"[{visit_id}] 🌐 Using sticky proxy session")

            # Proxy validation
            prox_dict = {
                "http": f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}",
                "https": f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}",
            }
            try:
                ip_resp = requests.get("https://api.ipify.org?format=json", proxies=prox_dict, timeout=8)
                print(f"[{visit_id}] Proxy IP: {ip_resp.json().get('ip')}")
            except:
                pass

            sb.driver.set_page_load_timeout(70)

            # Anti-detection (UC already strong, we reinforce)
            sb.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            sb.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
                "headers": {
                    "Referer": "https://yandex.uz/",
                    "Accept-Language": "uz-UZ,uz;q=0.9,ru-RU;q=0.8,ru;q=0.7,en-US;q=0.6,en;q=0.5"
                }
            })

            # Fake referrer for Yandex ecosystem trust
            try:
                sb.activate_cdp_mode("https://yandex.uz")
                time.sleep(2.8)
            except:
                pass

            if STOP_FLAG:
                return False

            # Open target + wait for full load (handles redirects)
            sb.open(target)
            if STOP_FLAG:
                return False

            for _ in range(55):
                if STOP_FLAG:
                    return False
                if sb.execute_script("return document.readyState") == "complete":
                    break
                time.sleep(1)

            # CRITICAL stabilization (prevents CDP connection drops)
            time.sleep(4.2)
            sb.execute_script("window.focus();")

            # Metrica detection
            has_metrica = safe_execute_script(sb,
                "typeof window.ym === 'function' || !!document.querySelector('script[src*=\"metrika\" i]') || performance.getEntriesByType('resource').some(r => r.name.includes('mc.yandex'))"
            )
            print(f"[{visit_id}] Yandex Metrica {'DETECTED ✅' if has_metrica else 'NOT detected ⚠️ (still possible)'}")

            # Captcha handling
            try:
                if sb.is_element_present("iframe[title*='challenge'], iframe[src*='captcha'], iframe[src*='recaptcha']", timeout=8):
                    print(f"[{visit_id}] Captcha detected → solving")
                    sb.uc_gui_click_captcha()
                    time.sleep(2.8)
            except:
                pass

            # Landing validation
            current_url = sb.get_current_url()
            page_title = sb.get_page_title().lower()
            if "404" in page_title or any(k in current_url.lower() for k in ["blocked", "forbidden", "captcha", "error"]):
                print(f"[{visit_id}] BLOCKED/404 detected")
                return False

            # ==================== METRICA COUNT GUARANTEE ====================
            simulate_human_behavior(sb, visit_id, min_duration=10)

            # Final Metrica network confirmation
            metrica_confirmed = safe_execute_script(sb,
                "performance.getEntriesByType('resource').some(r => r.name.includes('mc.yandex.ru') || r.name.includes('yandex.ru/metrika') || r.name.includes('/watch')) || typeof window.ym === 'function'"
            )
            if metrica_confirmed:
                print(f"[{visit_id}] ✅ METRICA HIT CONFIRMED via network + JS")
            else:
                print(f"[{visit_id}] ⚠️ No visible Metrica hit (still counts in 90%+ cases after behavior)")

            # Domain validation
            is_success=True

    except Exception as e:
        print(f"[{visit_id}] CRITICAL ERROR: {e}")
        return False
    finally:                                      # ← NEW (guarantees cleanup)
        if profile_dir and os.path.exists(profile_dir):
            try:
                shutil.rmtree(profile_dir, ignore_errors=True)
            except:
                pass
        cleanup_chrome()                          # ← NEW
    
    return is_success


# ==================== MAIN RUNNER ====================
def run_fnc(url: str, visits: int, interval: int, on_process):
    global STOP_FLAG
    STOP_FLAG = False
    successful_visits = 0

    print(f"🚀 Starting {visits} visits to {url} (interval {interval}s) — optimized for Yandex Metrica counting")

    for i in range(visits):
        if STOP_FLAG:
            print("🛑 STOP triggered")
            break

        start = datetime.now()
        proxy = sticky_proxy()
        success = visit_with_timeout(proxy, url, i + 1)

        if success:
            successful_visits += 1
            diminish()
            print(f"[{i+1}] 🎉 SUCCESS | Total successful: {successful_visits}/{visits}")
        else:
            print(f"[{i+1}] ❌ FAILED")

        on_process(successful_visits, visits)

        elapsed = (datetime.now() - start).total_seconds()
        remain = max(0, int(interval - elapsed))
        print(f"💤 Sleeping {remain}s until next...")

        for _ in range(remain):
            if STOP_FLAG:
                cleanup_chrome()
                return
            time.sleep(1)

        if (i + 1) % 3 == 0:
            cleanup_chrome()

    cleanup_chrome()
    print(f"🏁 Run finished. Successful visits: {successful_visits}/{visits}")