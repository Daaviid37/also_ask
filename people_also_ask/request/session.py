import os
import logging
import requests
import traceback
import time
import random
from people_also_ask.tools import retryable
from itertools import cycle
from typing import Optional
from threading import Semaphore
from people_also_ask.tools import CallingSemaphore
from people_also_ask.exceptions import RequestError

from requests import Session as _Session
from random import choice
HEADERS = {}
SESSION = _Session()
NB_TIMES_RETRY = os.environ.get("RELATED_QUESTION_NB_TIMES_RETRY", 3)
NB_REQUESTS_LIMIT = os.environ.get("RELATED_QUESTION_NB_REQUESTS_LIMIT", 25)
NB_REQUESTS_DURATION_LIMIT = os.environ.get("RELATED_QUESTION_NB_REQUESTS_DURATION_LIMIT", 60)  # seconds

logging.basicConfig()
semaphore = Semaphore(1)

# 2. Lista de cabezales de navegador (User-Agents)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.135 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:79.0) Gecko/20100101 Firefox/79.0",
    "Mozilla/5.0 (Windows NT 10.0; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.132 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36 Edge/17.17134",
    "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 6.1; Trident/7.0; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/44.0.2403.157 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.2; WOW64; Trident/7.0; AS; rv:11.0) like Gecko",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.84 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:62.0) Gecko/20100101 Firefox/62.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:60.0) Gecko/20100101 Firefox/60.0",
]

def set_headers(headers):
    global HEADERS
    HEADERS.update(headers)

def get_random_user_agent():
    return choice(USER_AGENTS)

logger = logging.getLogger(__name__)

class ProxyGeneator:

    def __init__(self, proxies: Optional[tuple]):
        self.proxies = proxies

    @property
    def iter_proxy(self):
        if not self.proxies:
            raise ValueError("No proxy found")
        if getattr(self, "_iter_proxy", None) is None:
            self._iter_proxy = cycle(self.proxies)
        return self._iter_proxy

    def get(self) -> dict:
        if not self.proxies:
            return {}
        proxy = next(self.iter_proxy)
        if not proxy.startswith("https"):
            proxy = f"http://{proxy}"
        return {
            "https": proxy
        }

def _load_proxies() -> Optional[tuple]:
    filepath = os.getenv("PAA_PROXY_FILE")
    if filepath:
        with open(filepath, "w") as fd:
            proxies = [e.strip() for e in fd.read().splitlines() if e.strip()]
    else:
        proxies = None
    return proxies

def set_proxies(proxies: Optional[tuple]) -> ProxyGeneator:
    global PROXY_GENERATORS
    PROXY_GENERATORS = ProxyGeneator(proxies=proxies)

set_proxies(proxies=_load_proxies())

@retryable(NB_TIMES_RETRY)
def get(url: str, params) -> requests.Response:
    proxies = PROXY_GENERATORS.get()
    try:
        with semaphore:
            response = SESSION.get(
                url,
                params=params,
                headers={"User-Agent": get_random_user_agent()},
                proxies=proxies,
            )
            time.sleep(random.uniform(10, 45))
    except Exception:
        raise RequestError(
            url, params, proxies, traceback.format_exc()
        )
    if response.status_code != 200:
        raise RequestError(
            url, params, proxies, response.text
        )
    return response
