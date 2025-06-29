import logging
import random
import time
from typing import Dict
import requests

logger = logging.getLogger(__name__)


class Proxy:
    # Mapping from proxy string ("host:port") to last-used timestamp (float). A value of
    # ``0`` means the proxy has never been used before.
    __proxies: Dict[str, float] = {}

    def __init__(self, api_key):
        self.__headers = {"Authorization": f"Token {api_key}"}

        self.__public_ip = self.get_public_ip()

        authorized_ip = self.get_ip_authorization()

        if authorized_ip:
            if authorized_ip["ip_address"] == self.__public_ip:
                logger.info("Current IP is already authorized")
                return

            logger.info(
                "Replacing authorized ip %s with current public IP",
                authorized_ip["ip_address"],
            )
            self.delete_ip_authorization(authorized_ip["id"])

        self.authorize_ip()

    def get_public_ip(self):
        response = requests.get(
            "https://proxy.webshare.io/api/v2/proxy/ipauthorization/whatsmyip/",
            headers=self.__headers,
        )

        ip = response.json()["ip_address"]
        logger.info("Public IP is %s", ip)
        return ip

    def get_ip_authorization(self):
        response = requests.get(
            "https://proxy.webshare.io/api/v2/proxy/ipauthorization/",
            headers=self.__headers,
        )
        results = response.json()["results"]
        if len(results) == 0:
            return None
        return results[0]

    def delete_ip_authorization(self, ip_address_id):
        logger.info("Deleting authorized ip with id %d", ip_address_id)
        response = requests.delete(
            f"https://proxy.webshare.io/api/v2/proxy/ipauthorization/{ip_address_id}/",
            headers=self.__headers,
        )

        if response.status_code != 204:
            raise requests.HTTPError(f"Could not delete ip authorization: {response}")

    def authorize_ip(self):
        logger.info("Authorizing IP %s", self.__public_ip)
        response = requests.post(
            "https://proxy.webshare.io/api/v2/proxy/ipauthorization/",
            json={"ip_address": self.__public_ip},
            headers=self.__headers,
        )

        if response.status_code != 201:
            raise requests.HTTPError(f"Could not authorize IP for proxy: {response}")

    def refresh(self):
        logger.info("Getting proxy list")

        response = requests.get(
            "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=100",
            headers=self.__headers,
        )

        proxy_details = response.json()["results"]
        proxies = [
            f"{proxy['proxy_address']}:{proxy['port']}" for proxy in proxy_details
        ]

        random.shuffle(proxies)

        logger.info("Got %d proxies", len(proxies))

        proxy_set = set(proxies)

        proxy_store = self.__class__.__proxies  # mutate class-level store

        # Add new proxies with a last_used timestamp of 0 (never used).
        for proxy in proxy_set - set(proxy_store):
            proxy_store[proxy] = 0.0

        # Remove proxies that are no longer present in the refreshed list.
        for proxy in list(proxy_store.keys()):
            if proxy not in proxy_set:
                del proxy_store[proxy]

    def get(self):
        proxy_store = self.__class__.__proxies

        if not proxy_store:
            self.refresh()

        # Re-fetch after potential refresh
        proxy_store = self.__class__.__proxies

        # Select the proxy that was used least recently.
        proxy = min(proxy_store, key=proxy_store.get)

        # Update its last-used timestamp to now.
        proxy_store[proxy] = time.time()

        return proxy
