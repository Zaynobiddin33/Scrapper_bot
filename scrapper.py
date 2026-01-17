from seleniumbase import SB
import time
import random
import os
import sys
import requests
from tokens import *

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

MAX_RETRIES_PER_PROXY = 2
TOTAL_VISITS = 15


def visit_with_proxy(proxy: dict, target, visit_id: int) -> bool:
    """Returns True if visit succeeded, False otherwise"""

    proxy_string = f"{proxy['username']}:{proxy['password']}@" \
                   f"{proxy['host']}:{proxy['port']}"

    try:
        with SB(
            uc=True,
            proxy=proxy_string,
            # block_images=True,
            headless=True,      # safer for captchas
            page_load_strategy="eager",
        ) as sb:

            print(f"[{visit_id}] Using proxy {proxy['host']}")
            # r = requests.get("https://api.ipify.org", proxies=prxys, timeout=10)
            # print("Proxy IP:", r.text)

            sb.open(target)
            time.sleep(2)

            # Handle redirects (captcha pages often redirect)
            current_url = sb.get_current_url()
            print(f"[{visit_id}] Landed on: {current_url}")

            # CAPTCHA handling
            if sb.is_element_present("iframe"):
                print(f"[{visit_id}] Possible CAPTCHA detected")
                sb.solve_captcha()
                time.sleep(2)

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


def run_fnc(url, visits):
    visit_count = 1

    for i in range(visits):
        proxy = PROXIES[0]

        for attempt in range(MAX_RETRIES_PER_PROXY):
            success = visit_with_proxy(proxy, url, visit_count)

            if success:
                visit_count += 1
                break

            print(f"[{visit_count}] Retrying with new proxy...")
            proxy = random.choice(PROXIES)
            time.sleep(random.uniform(1.5, 3.0))
        sleepin_time = random.randint(3, 10)
        print(f"sleep for {sleepin_time}s")
        time.sleep(sleepin_time)

