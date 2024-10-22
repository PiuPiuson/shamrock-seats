import logging
import time
import tempfile
import math
import os

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ryanair import (
    Ryanair,
    FlightNotFoundError,
    FlightSoldOutError,
    SeatsNotAvailableError,
    RyanairScriptError,
    SeatSelectionError,
)
from proxy import Proxy

# Flight details
ORIGIN = "STN"
DESTINATION = "OSL"
DEPARTURE_TIME = "06:30"
TARGET_SEAT = "02E"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_webdriver(proxy_ip: str = None):
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

    if proxy_ip:
        options.add_argument(f"--proxy-server=http://{proxy_ip}")

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
    proxies = Proxy(os.getenv("PROXY_API_KEY"))

    driver = create_webdriver()
    ra = Ryanair(driver, ORIGIN, DESTINATION, DEPARTURE_TIME)

    try:
        # Open the search page and accept cookies
        available_seats = ra.get_available_seats_in_flight()

        if TARGET_SEAT not in available_seats:
            raise SeatSelectionError(f"Target seat {TARGET_SEAT} is not available")

        available_seats.remove(TARGET_SEAT)

        logger.info(
            "There are %d available seats in the flight excluding selection",
            len(available_seats),
        )

    except (FlightNotFoundError, FlightSoldOutError, SeatsNotAvailableError) as e:
        logger.error("Flight error: %s", e)
        return
    except RyanairScriptError as e:
        logger.error("Script error: %s", e)
        return
    except Exception as e:
        logger.error("An unexpected error occurred: %s", e)
        return
    finally:
        driver.quit()

    driver = create_webdriver()
    ra = Ryanair(driver, ORIGIN, DESTINATION, DEPARTURE_TIME)

    try:
        # Open the search page and accept cookies
        available_tickets = ra.get_number_of_tickets_available()

        logger.info(
            "There are %d available tickets in the flight",
            available_tickets,
        )

    except (FlightNotFoundError, FlightSoldOutError, SeatsNotAvailableError) as e:
        logger.error("Flight error: %s", e)
        return
    except RyanairScriptError as e:
        logger.error("Script error: %s", e)
        return
    finally:
        driver.quit()

    # Calculate how many drivers we need
    drivers_needed = math.ceil(len(available_seats) / available_tickets)
    logger.info("Need to create %d chrome drivers", drivers_needed)

    proxy_list = proxies.get_proxy_list()

    if drivers_needed > len(proxy_list):
        logger.error(
            "Only %d proxies available. Cannot guarantee seat selection",
            len(proxy_list),
        )
        return

    seats_remaining = available_seats

    drivers = []
    ras = []
    for i in range(drivers_needed):
        try:
            logger.info("Starting session %d", i + 1)

            driver = create_webdriver(proxy_list.pop())
            drivers.append(driver)

            ra = Ryanair(driver, ORIGIN, DESTINATION, DEPARTURE_TIME)
            ras.append(ra)

            num_seats_to_reserve = (
                available_tickets
                if len(seats_remaining) >= available_tickets
                else len(seats_remaining)
            )

            logger.info(
                "Session %d needs to reserve %d seats", i + 1, num_seats_to_reserve
            )

            seats_to_reserve = seats_remaining[:num_seats_to_reserve]

            ra.reserve_seats(seats_to_reserve)

            logger.info("Session %d seats reserved", i + 1)

            seats_remaining = [
                seat for seat in seats_remaining if seat not in seats_to_reserve
            ]

        except (FlightNotFoundError, FlightSoldOutError, SeatsNotAvailableError) as e:
            logger.error("Flight error in session %d: %s", i + 1, e)
        except RyanairScriptError as e:
            logger.error("Script error in session %d: %s", i + 1, e)
        finally:
            driver.quit()

    logger.info("Waiting for user to make booking")
    time.sleep(60)

    for ra in ras:
        try:
            ra.free_reserved_seats()
        except RyanairScriptError as e:
            logger.error("Error freeing seats: %s", e)

    # Close all WebDriver instances
    for driver in drivers:
        driver.quit()
    logger.info("All sessions closed.")


if __name__ == "__main__":
    main()
