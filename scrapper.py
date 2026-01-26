from seleniumbase import SB
import time
import random
import os
import sys
import requests
from tokens import *
from datetime import datetime
import uuid
import subprocess

def set_stop_flag(value: bool):
    global STOP_FLAG
    STOP_FLAG = value

def cleanup_chrome():
    import psutil
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if "chrome" in proc.info['name'].lower() or "driver" in proc.info['name'].lower():
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

PROXIES = [
    {
        "host": PROXY_HOST,
        "port": PROXY_PORT,
        "username": USERNAME,
        "password": PASSWORD,
    },
    # add more proxies here
]
def new_session():
    return uuid.uuid4().hex[:8]

def sticky_proxy():
    session_id = uuid.uuid4().hex[:8]
    return {
        "host": PROXY_HOST,
        "port": PROXY_PORT,
        "username": f"{USERNAME}_session-{session_id}",
        "password": PASSWORD,
    }


MAX_RETRIES_PER_PROXY = 1


def visit_with_proxy(proxy: dict, target, visit_id: int) -> bool:
    """Returns True if visit succeeded, False otherwise"""

    proxy_string = f"{proxy['username']}:{proxy['password']}@" \
                   f"{proxy['host']}:{proxy['port']}"

    try:
        with SB(
            uc=True,
            proxy=proxy_string,
            # block_images=True,
            headless=False,      # safer for captchas
            page_load_strategy="eager",
            test=True,
            
        ) as sb:
            if STOP_FLAG: return
            is_success = False
            time.sleep(1)
            print(f"[{visit_id}] Using proxy {proxy['host']}")
    
            if STOP_FLAG: return

            sb.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            if STOP_FLAG: return
            # Before   sb.open(), set the referer
            sb.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
                "headers": {
                    "Referer": "https://yandex.ru/",
                    "Accept-Language": "uz-UZ,uz;q=0.9,ru-RU;q=0.8,ru;q=0.7,en-US;q=0.6,en;q=0.5"
                }
            })

            if STOP_FLAG: return
            sb.activate_cdp_mode("https://yandex.uz")
            sb.sleep(3)

            if STOP_FLAG: return
            # Replace sb.open(target) with this:
            sb.open(target)

            if STOP_FLAG: return

            try:
                if sb.wait_for_element_present("iframe", timeout=15):
                    print("Iframe detected, checking for captcha...")
                    
                    # 2. Give the captcha a moment to generate its internal tokens
                    sb.sleep(2) 
                    
                    # 3. Use SeleniumBase's specialized UC captcha solver
                    # This handles the click and the 'human-like' movement
                    sb.uc_gui_click_captcha()
            except:
                pass
            
            if STOP_FLAG: return
            time.sleep(5)

            if STOP_FLAG: return
            sb.uc_gui_click_captcha()

            if STOP_FLAG: return
            # Handle redirects (captcha pages often redirect)
            current_url = sb.get_current_url()
            print(f"[{visit_id}] Landed on: {current_url}")

            if STOP_FLAG: return
            if "404" in sb.get_page_title():
                print(f"[{visit_id}] Detected 404 Block. Attempting refresh...")
                return False

            # CAPTCHA handling

            for i in range(5):
                sys.stdout.write(f"\rProgress: {5-i}")
                sys.stdout.flush()
                time.sleep(1)
            
            if STOP_FLAG: return
            sb.execute_script("window.scrollBy(0,200)")
            time.sleep(1)
            if STOP_FLAG: return
            sb.execute_script("window.scrollBy(0,400)")
            time.sleep(0.5)
            if STOP_FLAG: return
            sb.execute_script("window.scrollBy(0,600)")
            time.sleep(2)
            if STOP_FLAG: return
            sb.execute_script("window.scrollBy(0,400)")
            time.sleep(2)


            # Extra check after CAPTCHA
            if "captcha" in sb.get_current_url().lower():
                print(f"[{visit_id}] CAPTCHA redirect detected")
                sb.solve_captcha()
                time.sleep(2)

            # Final validation
            if sb.get_current_url():
                print(f"[{visit_id}] Visit successful")
                is_success = True

            return is_success
        
    except Exception as e:
        print(f"[{visit_id}] Error: {e}")

    return False


def run_fnc(url, visits, interval, on_process):
    global STOP_FLAG
    visit_count = 1
    STOP_FLAG = False  # Reset flag

    for i in range(visits):
        if STOP_FLAG: break # Stop outer loop

        start = datetime.now()
        proxy = sticky_proxy()

        success = visit_with_proxy(proxy, url, visit_count)
        visit_count+=1
        
        # Smart Sleep
        time.sleep(random.uniform(1.5, 3.0))

        end = datetime.now()
        on_process(i+1, visits)
        
        elapsed = (end - start).total_seconds()
        remain = int(interval - elapsed) if int(interval - elapsed) > 0 else 0
        
        print(f'sleeping {remain} seconds')
        
        # Instant Stop during sleep
        for _ in range(remain):
            if STOP_FLAG:
                print("Stopped: cleaning chrome up")
                cleanup_chrome()
                return
            time.sleep(1)
        if (i+1) % 3 == 0:
            print("another 5th step done: cleaning chrome")
            cleanup_chrome()
        
        if STOP_FLAG:
            break
    cleanup_chrome()