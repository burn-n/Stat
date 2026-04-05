import requests
import threading
import queue
import itertools
import time
import string

API = "https://discord.com/api/v9/unique-username/username-attempt-unauthed"
WEBHOOK = "https://discord.com/api/webhooks/1490243245198807133/zqmeds9xpArPDcLh9VsyST6bSSp7EVOr2OWH9D6Zj-kIhp-qvyyKyT8XHuBa6FrdpRYi"

THREADS = 1
COOLDOWN = 10
MAX_RETRIES = 5

CHARS = string.ascii_lowercase + string.digits + "_" + "."  # a-z + 0-9

# load proxies (optional)
try:
    with open("proxies.txt", "r") as f:
        proxies = [p.strip() for p in f if p.strip()]
except:
    proxies = []

proxy_cycle = itertools.cycle(proxies) if proxies else None
use_proxies = False

request_lock = threading.Lock()

q = queue.Queue()

# generate 3 and 4 character usernames
def generate_names():
    for length in [3, 4]:
        for combo in itertools.product(CHARS, repeat=length):
            yield ''.join(combo)

for name in generate_names():
    q.put(name)


def send_webhook(name):
    if not WEBHOOK:
        return

    try:
        requests.post(WEBHOOK, json={
            "content": f"🔥 AVAILABLE: `{name}`"
        }, timeout=5)
    except:
        pass


def get_proxy():
    if not use_proxies or not proxy_cycle:
        return None

    proxy = next(proxy_cycle)
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
            r = requests.post(
                API,
                json={"username": name},
                proxies=get_proxy(),
                timeout=10
            )

            if r.status_code == 200:
                data = r.json()

                if data.get("taken", True):
                    print(f"TAKEN : {name}")
                else:
                    print(f"OPEN  : {name}")

                    with open("hits.txt", "a") as f:
                        f.write(name + "\n")

                    send_webhook(name)

                return

            elif r.status_code == 429:
                with request_lock:
                    print("RATE LIMITED → enabling proxies")
                    use_proxies = True

                retries += 1
                time.sleep(2)

            else:
                print(f"ERROR {r.status_code} : {name}")
                return

        except Exception as e:
            print(f"REQUEST ERROR : {name} ({e})")
            retries += 1
            time.sleep(2)

    print(f"GAVE UP : {name}")


def worker():
    while True:
        try:
            name = generate_names()
        except queue.Empty:
            return
        
        check(name)
        q.task_done()


# start threads
threads = []
for _ in range(THREADS):
    t = threading.Thread(target=worker)
    t.start()
    threads.append(t)

for t in threads:
    t.join()

print("Done")
