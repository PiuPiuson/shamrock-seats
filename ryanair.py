import logging
import random
import string
import time
from typing import Optional

from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

TIMEOUT = 40

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Ryanair:
    def __init__(self, web_driver):
        self.driver = web_driver
        self.num_passengers = 25

    @staticmethod
    def generate_random_string(length: Optional[int] = None) -> str:
        """Generate a random string of specified length."""
        if length is None:
            length = random.randint(3, 7)
        return "".join(random.choices(string.ascii_letters, k=length))

    @staticmethod
    def generate_search_url(
        date: str, origin: str, destination: str, people: int = 1
    ) -> str:
        """Generate the URL to search flights. Date should be 'YYYY-MM-DD'."""
        return (
            f"https://www.ryanair.com/gb/en/trip/flights/select?"
            f"adults={people}&teens=0&children=0&infants=0&dateOut={date}&dateIn=&"
            f"isConnectedFlight=false&discount=0&promoCode=&isReturn=false&"
            f"originIata={origin}&destinationIata={destination}&tpAdults={people}&"
            f"tpTeens=0&tpChildren=0&tpInfants=0&tpStartDate={date}&tpEndDate=&"
            f"tpDiscount=0&tpPromoCode=&tpOriginIata={origin}&tpDestinationIata={destination}"
        )

    def accept_cookies(self):
        """Accept cookies on the website."""
        try:
            accept_button = WebDriverWait(self.driver, TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-ref="cookie.accept-all"]')
                )
            )
            accept_button.click()
            logger.info("Accepted cookies.")
        except (TimeoutException, NoSuchElementException):
            logger.warning("Cookie acceptance button not found or not clickable.")

    def flights_exist(self) -> bool:
        """Check if flights exist with the given parameters."""
        try:
            self.driver.find_element(By.CSS_SELECTOR, ".no-flights")
            logger.info("No flights found.")
            return False
        except NoSuchElementException:
            logger.info("Flights are available.")
            return True

    def get_flight_card(self, flight_number: str):
        """Retrieve the flight card element matching the flight number."""
        try:
            WebDriverWait(self.driver, TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".card-flight-num__content")
                )
            )
            flight_number_containers = self.driver.find_elements(
                By.CSS_SELECTOR, ".card-flight-num__content"
            )

            for flight_container in flight_number_containers:
                if flight_container.text.strip().replace(" ", "") == flight_number:
                    parent_element = flight_container.find_element(
                        By.XPATH, "./ancestor::*[contains(@class, 'flight-card')]"
                    )
                    return parent_element
            logger.warning(f"Flight number {flight_number} not found.")
            return None
        except TimeoutException:
            logger.error("Timeout while searching for flight cards.")
            return None

    def is_flight_sold_out(self, flight_card):
        """Checks if a flight on a flight card is sold out"""
        try:
            flight_card.find_element(
                By.CSS_SELECTOR, "flights-lazy-sold-out-flight-card"
            )
            return True
        except NoSuchElementException:
            return False

    def make_gender_dropdown_selection(self, passenger_card):
        """Select 'Mr' from the gender dropdown."""
        try:
            dropdown_toggle = WebDriverWait(passenger_card, 10).until(
                EC.element_to_be_clickable(
                    (
                        By.CSS_SELECTOR,
                        'ry-dropdown[data-ref="pax-details__title"] button.dropdown__toggle',
                    )
                )
            )
            dropdown_toggle.click()

            mr_option = WebDriverWait(passenger_card, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ry-dropdown-item"))
            )
            mr_option.click()
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Error selecting gender: {e}")

    def populate_passenger_form(self, passenger_card):
        """Populate the name and surname fields with random data."""
        try:
            name_inputs = passenger_card.find_elements(
                By.CSS_SELECTOR, "input[name*='form.passengers.']"
            )

            for name in name_inputs:
                name.send_keys(self.generate_random_string())

        except NoSuchElementException as e:
            logger.error(f"Error populating name form: {e}")

    def first_page(self, date: str, origin: str, destination: str, flight_number: str):
        """Perform actions on the first page."""
        self.driver.get(self.generate_search_url(date, origin, destination))
        self.accept_cookies()

        if not self.flights_exist():
            logger.error("No flights exist with the given parameters.")
            return

        flight_card = self.get_flight_card(flight_number)
        if flight_card is None:
            logger.error("Could not find the specified flight.")
            return

        logger.info("Flight number %s found.", flight_number)

        if self.is_flight_sold_out(flight_card):
            logger.error("Selected flight is sold out. Script can't run")
            return

        logger.info("Finding maximum available seats")
        while True:
            self.driver.get(
                self.generate_search_url(date, origin, destination, self.num_passengers)
            )

            flight_card = self.get_flight_card(flight_number)
            if flight_card is None:
                logger.error("Could not find the specified flight.")
                return

            if self.is_flight_sold_out(flight_card):
                self.num_passengers -= 1
            else:
                break

        logger.info("There are %d seats available", self.num_passengers)

        try:
            select_button = flight_card.find_element(
                By.CSS_SELECTOR, ".flight-card-summary__select-btn"
            )
            select_button.click()
            logger.info("Selected the flight.")

            recommended_fare = WebDriverWait(self.driver, TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".fare-table__fare-column-border--recommended")
                )
            )
            recommended_fare.click()
            logger.info("Selected recommended fare.")

            login_later_button = WebDriverWait(self.driver, TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".login-touchpoint__login-later")
                )
            )
            login_later_button.click()
            logger.info("Chose to login later.")

            passenger_forms = self.driver.find_elements(By.CSS_SELECTOR, ".passenger")

            for form in passenger_forms:
                self.make_gender_dropdown_selection(form)
                self.populate_passenger_form(form)

            logger.info("Populated name and surname fields.")

            continue_button = self.driver.find_element(
                By.CSS_SELECTOR, ".continue-flow__button"
            )
            continue_button.click()
            logger.info("Proceeded to the next page.")
        except (TimeoutException, NoSuchElementException) as e:
            logger.error(f"Error on the first page: {e}")

    def select_seats_page(self, target_seat: str):
        """Perform actions on the second page."""
        WebDriverWait(self.driver, TIMEOUT).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".seatmap__seat"))
        )

        available_seats = self.driver.find_elements(
            By.CSS_SELECTOR, ".seatmap__seat:not([class*='unavailable'])"
        )

        logger.info("There are %d available seats", len(available_seats))

        seat_ids = [
            seat.get_attribute("id")
            for seat in available_seats
            if seat.get_attribute("id").strip()
        ]

        target_seat_id = f"seat-{target_seat}"
        if target_seat_id in seat_ids:
            seat_ids.remove(target_seat_id)

        if not seat_ids:
            logger.warning("No other available seats to select.")
            return

        for i in range(self.num_passengers):
            selected_seat_id = seat_ids[i]
            seat_element = self.driver.find_element(
                By.CSS_SELECTOR, f"#{selected_seat_id}"
            )
            self.driver.execute_script("arguments[0].click();", seat_element)
            logger.info("Selected seat %s for passenger %d.", selected_seat_id, i + 1)

        next_button = self.driver.find_element(
            By.CSS_SELECTOR, ".passenger-carousel__cta--next"
        )
        next_button.click()
        logger.info("Clicked on continue.")

        add_fast_track_button = WebDriverWait(self.driver, TIMEOUT).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".enhanced-takeover-beta__product-confirm-cta")
            )
        )
        add_fast_track_button.click()
        logger.info("Added fast track.")

    def run(
        self,
        date: str,
        origin: str,
        destination: str,
        flight_number: str,
        target_seat: str,
    ):
        """Run the bot with specified parameters."""

        self.first_page(date, origin, destination, flight_number)
        self.select_seats_page(target_seat)
