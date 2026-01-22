from seleniumbase import SB
import time
import random
import os
import sys
import requests
from tokens import *
from datetime import datetime

PROXIES = [
    {
        "host": PROXY_HOST,
        "port": PROXY_PORT,
        "username": USERNAME,
        "password": PASSWORD,
    },
    # add more proxies here
]
prxy = f"http://{PROXIES[0]['username']}:{PROXIES[0]['password']}@{PROXIES[0]['host']}:{PROXIES[0]['port']}"

prxys = {
    'http': prxy,
    'https': prxy
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
            
            time.sleep(2)
            print(f"[{visit_id}] Using proxy {proxy['host']}")
            r = requests.get("http://api.ipify.org", proxies=prxys, timeout=10)
            print("Proxy IP:", r.text)

            sb.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Before   sb.open(), set the referer
            sb.execute_cdp_cmd("Network.setExtraHTTPHeaders", {
                "headers": {
                    "Referer": "https://yandex.ru/",
                    "Accept-Language": "uz-UZ,uz;q=0.9,ru-RU;q=0.8,ru;q=0.7,en-US;q=0.6,en;q=0.5"
                }
            })
            sb.activate_cdp_mode("https://yandex.uz")
            sb.sleep(3)

            # Replace sb.open(target) with this:
            sb.uc_open_with_reconnect(target, reconnect_time=5)
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

            time.sleep(10)


            sb.uc_gui_click_captcha()

            # Handle redirects (captcha pages often redirect)
            current_url = sb.get_current_url()
            print(f"[{visit_id}] Landed on: {current_url}")

            if "404" in sb.get_page_title():
                print(f"[{visit_id}] Detected 404 Block. Attempting refresh...")
                sb.sleep(2)
                sb.refresh()

            # CAPTCHA handling

            for i in range(5):
                sys.stdout.write(f"\rProgress: {5-i}")
                sys.stdout.flush()
                time.sleep(1)

            sb.execute_script("window.scrollBy(0,200)")
            time.sleep(1)
            sb.execute_script("window.scrollBy(0,400)")
            time.sleep(0.5)
            sb.execute_script("window.scrollBy(0,600)")
            time.sleep(2)
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
                return True
    except Exception as e:
        print(f"[{visit_id}] Error: {e}")

    return False


def run_fnc(url, visits, interval, on_process):
    visit_count = 1

    for i in range(visits):
        start = datetime.now()
        proxy = PROXIES[0]

        for attempt in range(MAX_RETRIES_PER_PROXY):
            success = visit_with_proxy(proxy, url, visit_count)

            if success:
                visit_count += 1
                break

            print(f"[{visit_count}] Retrying with new proxy...")
            proxy = random.choice(PROXIES)
            time.sleep(random.uniform(1.5, 3.0))
        end = datetime.now()
        on_process(i+1, visits)
        remain = int(interval-(end-start).total_seconds())
        for i in range(remain):
            sys.stdout.write(f'\r{remain-i} remaining')
            sys.stdout.flush()
            time.sleep(1)
        
