import logging
import time
import tempfile
import math
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ryanair import Ryanair

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    # Flight details
    date = "2024-10-21"
    origin = "STN"
    destination = "KRK"
    flight_number = "FR2362"
    target_seat = "02B"

    # Initialize a WebDriver to get the list of available seats
    options = webdriver.ChromeOptions()
    options.add_argument("--incognito")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
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
        ra.driver.quit()

    options = webdriver.ChromeOptions()
    options.add_argument("--incognito")
    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )
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
        ra.driver.quit()

    # Calculate how many drivers we need
    drivers_needed = math.ceil(len(available_seats) / available_tickets)
    logger.info("Need to create %d chrome drivers", drivers_needed)

    seats_remaining = available_seats

    drivers = []
    # for i in range(drivers_needed):
    for i in range(1):
        try:
            logger.info("Starting session %d", i + 1)

            user_data_dir = tempfile.mkdtemp()

            # Initialize ChromeOptions
            options = webdriver.ChromeOptions()
            options.add_argument("--incognito")
            options.add_argument(f"--user-data-dir={user_data_dir}")

            # Initialize a new WebDriver with unique user profile
            driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()), options=options
            )
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

    # The drivers list contains all active WebDriver instances
    # Keep the browsers open for a specified time
    time_to_keep_open = 300
    logger.info("Keeping browsers open for %d seconds...", time_to_keep_open)
    time.sleep(time_to_keep_open)

    # Close all WebDriver instances
    for driver in drivers:
        driver.quit()
    logger.info("All sessions closed.")


if __name__ == "__main__":
    main()
