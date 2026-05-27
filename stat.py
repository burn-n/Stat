import requests
import threading
import queue
import itertools
import time
import string
import sys
import random

API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
WEBHOOK = "https://discord.com/api/webhooks/1508590349713408231/CIljNz9hoywwrkH9ZJ7cjWVwUi5gogPNdGlWXzYucncqQb13qZZpB6D-Vi6wCSaeZ4WT"

THREADS = 5
COOLDOWN = 15
MAX_RETRIES = 5

CHARS = string.ascii_lowercase + string.digits + "_" + "."

# load proxies (optional)
try:
    with open("proxies.txt", "r") as f:
        proxies = [p.strip() for p in f if p.strip()]
except:
    proxies = []

proxy_cycle = itertools.cycle(proxies) if proxies else None
use_proxies = False

request_lock = threading.Lock()

checked = set()
checked_lock = threading.Lock()


def log(msg):
    print(msg, flush=True)
    sys.stdout.flush()


log(f"[INIT] Loaded {len(proxies)} proxies")


def generate_random_username():
    while True:
        length = random.choice([3, 4])

        name = ''.join(random.choice(CHARS) for _ in range(length))

        with checked_lock:
            if name not in checked:
                checked.add(name)
                return name


def send_webhook(name):
    if not WEBHOOK:
        return

    try:
        requests.post(
            WEBHOOK,
            json={
                "content": f"🔥 AVAILABLE: `{name}`"
            },
            timeout=5
        )

        log(f"[WEBHOOK] Sent hit for {name}")

    except Exception as e:
        log(f"[WEBHOOK ERROR] {e}")


def get_proxy():
    if not use_proxies or not proxy_cycle:
        return None

    proxy = next(proxy_cycle)

    log(f"[PROXY] Using {proxy}")

    return {
        "http": f"http://{proxy}",
        "https": f"http://{proxy}"
    }


def check(name):
    global use_proxies

    retries = 0

    while retries < MAX_RETRIES:
        time.sleep(COOLDOWN)

        try:
            log(f"[CHECKING] {name}")

            r = requests.post(
                API,
                json={"username": name},
                proxies=get_proxy(),
                timeout=10
            )

            log(f"[RESPONSE] {name} -> {r.status_code}")

            if r.status_code == 200:
                data = r.json()

                if data.get("taken", True):
                    log(f"[TAKEN] {name}")
                else:
                    log(f"[OPEN] {name}")

                    with open("hits.txt", "a") as f:
                        f.write(name + "\n")

                    log(f"[SAVED] {name} -> hits.txt")

                    send_webhook(name)

                return

            elif r.status_code == 429:
                with request_lock:
                    log("[RATE LIMITED] Enabling proxies")
                    use_proxies = True

                retries += 1

                log(f"[RETRY] {name} ({retries}/{MAX_RETRIES})")

                time.sleep(2)

            else:
                log(f"[ERROR] {name} -> HTTP {r.status_code}")
                return

        except Exception as e:
            log(f"[REQUEST ERROR] {name} -> {e}")

            retries += 1

            log(f"[RETRY] {name} ({retries}/{MAX_RETRIES})")

            time.sleep(2)

    log(f"[GAVE UP] {name}")


def worker():
    while True:
        name = generate_random_username()

        check(name)

        log(f"[TOTAL CHECKED] {len(checked)}")


# start threads
threads = []

log(f"[START] Launching {THREADS} thread(s)")

for i in range(THREADS):
    t = threading.Thread(target=worker, name=f"worker-{i}")
    t.daemon = True
    t.start()

    log(f"[THREAD STARTED] worker-{i}")

    threads.append(t)

for t in threads:
    t.join()

log("[DONE] Finished checking usernames")
