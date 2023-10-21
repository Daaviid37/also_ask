import os
import logging
import requests
import traceback

from people_also_ask.tools import retryable
from itertools import cycle
from typing import Optional
from people_also_ask.tools import CallingSemaphore
from people_also_ask.exceptions import RequestError

from requests import Session as _Session

SESSION = _Session()

PROXIES = {
    "authentication": {
        "username": "MEzC3gIqJz",
        "password": "u8fFNx8ggW"
    },
    "list": [
        {"ip": "193.26.152.113", "port": "58542"},
        {"ip": "193.35.89.16", "port": "58542"},
        {"ip": "194.38.58.63", "port": "58542"},
        {"ip": "212.115.47.253", "port": "58542"},
        {"ip": "212.80.208.90", "port": "58542"},
        {"ip": "212.80.210.223", "port": "58542"},
        {"ip": "81.21.228.137", "port": "58542"},
        {"ip": "81.21.231.45", "port": "58542"},
        {"ip": "95.214.146.65", "port": "58542"},
        {"ip": "95.214.147.213", "port": "58542"}
    ]
}


def create_proxy_list(proxy_data):
    auth = proxy_data["authentication"]
    user = auth["username"]
    password = auth["password"]
    
    proxies = []
    for entry in proxy_data["list"]:
        ip = entry["ip"]
        port = entry["port"]
        proxy_str = f"http://{user}:{password}@{ip}:{port}"
        proxies.append(proxy_str)
    
    return tuple(proxies)

PROXY_LIST = create_proxy_list(PROXIES)

NB_TIMES_RETRY = os.environ.get(
    "RELATED_QUESTION_NB_TIMES_RETRY", 3
)
NB_REQUESTS_LIMIT = os.environ.get(
    "RELATED_QUESTION_NB_REQUESTS_LIMIT", 25
)
NB_REQUESTS_DURATION_LIMIT = os.environ.get(
    "RELATED_QUESTION_NB_REQUESTS_DURATION_LIMIT", 60  # seconds
)
logging.basicConfig()
semaphore = CallingSemaphore(
    NB_REQUESTS_LIMIT, NB_REQUESTS_DURATION_LIMIT
)
HEADERS = {
    'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    " AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/84.0.4147.135 Safari/537.36"
}

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
    return {
        "https": proxy
    }

PROXY_GENERATORS = ProxyGeneator(proxies=PROXY_LIST)

@retryable(NB_TIMES_RETRY)
def get(url: str, params) -> requests.Response:
    proxies = PROXY_GENERATORS.get()
    try:
        with semaphore:
            response = SESSION.get(
                url,
                params=params,
                headers=HEADERS,
                proxies=proxies,
            )
    except Exception:
        raise RequestError(
            url, params, proxies, traceback.format_exc()
        )
    if response.status_code != 200:
        raise RequestError(
            url, params, proxies, response.text
        )
    return response
