import logging
import time
import tempfile
import math
import requests
import os


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ryanair import Ryanair


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_public_ip():
    ip = requests.get("https://api.ipify.org").content.decode("utf8")
    logger.info("Public IP is %s", ip)
    return ip


PUBLIC_IP = get_public_ip()


def authorize_ip_for_proxy():
    logger.info("Authorizing IP for proxy")
    response = requests.post(
        "https://proxy.webshare.io/api/v2/proxy/ipauthorization/",
        json={"ip_address": PUBLIC_IP},
        headers={"Authorization": f"Token {os.getenv("PROXY_API_KEY")}"},
    )
    if response.status_code != 400:
        raise Exception("Could not authorize ip for proxy")


def get_proxies():
    logger.info("Getting proxy list")
    authorize_ip_for_proxy()

    response = requests.get(
        "https://proxy.webshare.io/api/v2/proxy/list/?mode=direct&page=1&page_size=50",
        headers={"Authorization": f"Token {os.getenv("PROXY_API_KEY")}"},
    )

    proxy_details = response.json()["results"]
    proxies = [f"{proxy['proxy_address']}:{proxy['port']}" for proxy in proxy_details]

    logger.info("Got %d proxies", len(proxies))
    return proxies


PROXIES = get_proxies()


def create_webdriver(use_proxy=False):
    options = webdriver.ChromeOptions()
    options.add_argument("--incognito")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_experimental_option(
        "prefs", {"profile.managed_default_content_settings.images": 2}
    )

    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")

    if use_proxy:
        options.add_argument(f"--proxy-server=http://{PROXIES.pop()}")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    ]

    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride", {"userAgent": user_agents[0]}
    )

    return driver


def main():
    # Flight details
    date = "2024-10-21"
    origin = "MAN"
    destination = "BCN"
    flight_number = "FR7542"
    target_seat = "01C"

    driver = create_webdriver()
    ra = Ryanair(driver)

    try:
        # Open the search page and accept cookies
        available_seats = ra.get_available_seats_in_flight(
            date, origin, destination, flight_number
        )

        if target_seat not in available_seats:
            logger.error("Target seat %s is not available", target_seat)
            return

        available_seats.remove(target_seat)

        logger.info(
            "There are %d available seats in the flight excluding selection",
            len(available_seats),
        )

    except Exception as e:
        logger.error("An error occurred: %s", e)
    finally:
        # Close the initial driver
        driver.quit()

    driver = create_webdriver()
    ra = Ryanair(driver)

    try:
        # Open the search page and accept cookies
        available_tickets = ra.get_number_of_tickets_available(
            date, origin, destination, flight_number
        )

        logger.info(
            "There are %d available tickets in the flight",
            available_tickets,
        )

    except Exception as e:
        logger.error("An error occurred: %s", e)
    finally:
        # Close the initial driver
        driver.quit()

    # Calculate how many drivers we need
    drivers_needed = math.ceil(len(available_seats) / available_tickets)
    logger.info("Need to create %d chrome drivers", drivers_needed)

    if drivers_needed > len(PROXIES):
        logger.error(
            "Only %d proxies available. Cannot guarantee seat selection", len(PROXIES)
        )
        return

    seats_remaining = available_seats

    drivers = []
    for i in range(drivers_needed):
        try:
            logger.info("Starting session %d", i + 1)

            driver = create_webdriver(use_proxy=True)
            drivers.append(driver)
            ra = Ryanair(driver)

            num_seats_to_reserve = (
                available_tickets
                if len(seats_remaining) >= available_tickets
                else len(seats_remaining)
            )

            logger.info(
                "Session %d needs to reserve %d seats", i + 1, num_seats_to_reserve
            )

            seats_to_reserve = seats_remaining[:num_seats_to_reserve]

            ra.reserve_seats(
                date,
                origin,
                destination,
                flight_number,
                seats_to_reserve,
            )

            logger.info("Session %d seats reserved", i + 1)

            print(len(seats_remaining))
            seats_remaining = [
                seat for seat in seats_remaining if seat not in seats_to_reserve
            ]

            print(len(seats_remaining))

        except Exception as e:
            logger.error("An error occurred in session %d: %s", i + 1, e)
            driver.quit()
            raise

    # Close all WebDriver instances
    for driver in drivers:
        driver.quit()
    logger.info("All sessions closed.")


if __name__ == "__main__":
    main()
