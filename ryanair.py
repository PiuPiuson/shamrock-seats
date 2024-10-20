import logging
import random
import string
from typing import List

from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Ryanair:
    TIMEOUT = 40  # Timeout for WebDriverWait

    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.num_passengers = 5

    @staticmethod
    def generate_random_string(length: int = 6) -> str:
        """Generate a random string of specified length."""
        return "".join(random.choices(string.ascii_letters, k=length))

    @staticmethod
    def generate_search_url(
        date: str, origin: str, destination: str, people: int = 1
    ) -> str:
        """Generate the URL to search flights. Date should be 'YYYY-MM-DD'."""
        base_url = "https://www.ryanair.com/gb/en/trip/flights/select"
        params = (
            f"?adults={people}"
            f"&teens=0&children=0&infants=0"
            f"&dateOut={date}"
            f"&originIata={origin}"
            f"&destinationIata={destination}"
            f"&isReturn=false"
            f"&discount=0"
            f"&promoCode="
            f"&isConnectedFlight=false"
        )
        return base_url + params

    def accept_cookies(self):
        """Accept cookies on the website."""
        try:
            accept_button = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[data-ref="cookie.accept-all"]')
                )
            )
            accept_button.click()
            logger.info("Accepted cookies.")
        except (
            TimeoutException,
            NoSuchElementException,
            ElementClickInterceptedException,
        ) as e:
            logger.warning("Cookie acceptance failed: %s", e)

    def flights_exist(self) -> bool:
        """Check if flights exist with the given parameters."""
        try:
            WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".flight-card"))
            )
            logger.info("Flights are available.")
            return True
        except TimeoutException:
            logger.info("No flights found.")
            return False

    def get_flight_card(self, flight_number: str):
        """Retrieve the flight card element matching the flight number."""
        try:
            flight_cards = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".flight-card"))
            )
            for card in flight_cards:
                try:
                    flight_number_element = card.find_element(
                        By.CSS_SELECTOR, ".card-flight-num__content"
                    )
                    flight_number_text = flight_number_element.text.strip().replace(
                        " ", ""
                    )
                    if flight_number_text == flight_number:
                        return card
                except NoSuchElementException:
                    continue
            logger.warning("Flight number %s not found.", flight_number)
            return None
        except TimeoutException:
            logger.error("Timeout while searching for flight cards.")
            return None

    def is_flight_sold_out(self, flight_card) -> bool:
        """Check if a flight is sold out."""
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
            dropdown_toggle = passenger_card.find_element(
                By.CSS_SELECTOR,
                'ry-dropdown[data-ref="pax-details__title"] button.dropdown__toggle',
            )
            dropdown_toggle.click()
            mr_option = passenger_card.find_element(
                By.CSS_SELECTOR, "ry-dropdown-item[data-ref='title-item-0']"
            )
            mr_option.click()
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            logger.error("Error selecting gender: %s", e)
            raise

    def populate_passenger_form(self, passenger_card):
        """Populate the name and surname fields with random data."""
        try:
            inputs = passenger_card.find_elements(
                By.CSS_SELECTOR, "input[name*='form.passengers.']"
            )
            for i in inputs:
                i.send_keys(self.generate_random_string())
        except NoSuchElementException as e:
            logger.error("Error populating name form: %s", e)
            raise

    def open_search_page(
        self, date: str, origin: str, destination: str, people: int = 1
    ):
        """Open the search page with the given parameters."""
        search_url = self.generate_search_url(date, origin, destination, people)
        self.driver.get(search_url)
        logger.info("Opened search page.")

    def find_available_seats(self, date, origin, destination, flight_number: str):
        """Find the maximum number of available seats for the specified flight."""
        while self.num_passengers > 0:
            self.open_search_page(date, origin, destination, self.num_passengers)
            flight_card = self.get_flight_card(flight_number)
            if not flight_card:
                logger.error("Could not find the specified flight.")
                return None
            if self.is_flight_sold_out(flight_card):
                self.num_passengers -= 1
                logger.info("Reducing passenger count to %d", self.num_passengers)
            else:
                logger.info(
                    "Found available seats for %d passengers.", self.num_passengers
                )
                return flight_card
        logger.error("No available seats found.")
        return None

    def select_flight(self, flight_card):
        """Select the specified flight."""
        try:
            select_button = WebDriverWait(flight_card, self.TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".flight-card-summary__select-btn")
                )
            )
            select_button.click()
            logger.info("Selected the flight.")
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            logger.error("Error selecting flight: %s", e)
            raise

    def select_fare(self):
        """Select the recommended fare."""
        try:
            recommended_fare = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".fare-table__fare-column-border--recommended")
                )
            )
            recommended_fare.click()
            logger.info("Selected recommended fare.")
        except (
            TimeoutException,
            NoSuchElementException,
            ElementClickInterceptedException,
        ) as e:
            logger.error("Error selecting fare: %s", e)
            raise

    def login_later(self):
        """Proceed without logging in."""
        try:
            login_later_button = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".login-touchpoint__login-later")
                )
            )
            login_later_button.click()
            logger.info("Chose to login later.")
        except (
            TimeoutException,
            NoSuchElementException,
            ElementClickInterceptedException,
        ) as e:
            logger.error("Error clicking 'Login Later' button: %s", e)
            raise

    def fill_passenger_details(self):
        """Fill in passenger details."""
        try:
            passenger_forms = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".passenger"))
            )
            for form in passenger_forms:
                self.make_gender_dropdown_selection(form)
                self.populate_passenger_form(form)
            logger.info("Populated passenger details.")
        except (TimeoutException, NoSuchElementException) as e:
            logger.error("Error filling passenger details: %s", e)
            raise

    def proceed_to_seats_page(self):
        """Click on the continue button to proceed to seats page."""
        try:
            continue_button = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".continue-flow__button"))
            )
            continue_button.click()
            logger.info("Proceeded to the seats page.")
        except (
            TimeoutException,
            NoSuchElementException,
            ElementClickInterceptedException,
        ) as e:
            logger.error("Error proceeding to seats page: %s", e)
            raise

    def proceed_to_fast_track(self):
        """Click on the continue button to proceed to fast track selection."""
        try:
            continue_button = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".passenger-carousel__cta--next")
                )
            )
            continue_button.click()
            logger.info("Proceeded to the fast track selection.")
        except (
            TimeoutException,
            NoSuchElementException,
            ElementClickInterceptedException,
        ) as e:
            logger.error("Error proceeding to fast track selection: %s", e)
            raise

    def wait_for_seatmap(self):
        """Wait until the seatmap is loaded."""
        try:
            WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".seatmap__seat"))
            )
            logger.info("Seatmap is loaded.")
        except TimeoutException as e:
            logger.error("Seatmap did not load in time: %s", e)
            raise

    def get_available_seats(self) -> List[str]:
        """Get a list of available seat IDs."""
        seats = self.driver.find_elements(
            By.CSS_SELECTOR, ".seatmap__seat:not([class*='unavailable'])"
        )
        available_seats = []
        for seat in seats:
            seat_id = seat.get_attribute("id")
            if seat_id:
                available_seats.append(seat_id)
        logger.info("There are %d available seats.", len(available_seats))
        return available_seats

    def select_seats(self, available_seats: List[str], target_seat: str):
        """Select seats for all passengers, excluding the target seat."""
        target_seat_id = f"seat-{target_seat}"
        if target_seat_id in available_seats:
            available_seats.remove(target_seat_id)
        else:
            raise Exception(f"Target seat {target_seat} not available.")

        if len(available_seats) < self.num_passengers:
            raise Exception("Not enough available seats for all passengers.")

        for i in range(self.num_passengers):
            seat_id = available_seats[i]
            try:
                seat_element = self.driver.find_element(By.CSS_SELECTOR, f"#{seat_id}")
                self.driver.execute_script("arguments[0].click();", seat_element)
                logger.info("Selected seat %s for passenger %d.", seat_id, i + 1)
            except NoSuchElementException as e:
                logger.error("Error selecting seat %s: %s", seat_id, e)
                raise

    def handle_add_fast_track(self):
        """Handle the fast track page."""
        try:
            add_fast_track_button = WebDriverWait(self.driver, self.TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, ".enhanced-takeover-beta__product-confirm-cta")
                )
            )
            add_fast_track_button.click()
            logger.info("Added fast track.")
        except (
            TimeoutException,
            NoSuchElementException,
            ElementClickInterceptedException,
        ) as e:
            raise Exception("Error adding fast track: %s", e)

    def select_seats_page(self, target_seat: str):
        """Perform actions on the seat selection page."""
        self.wait_for_seatmap()

        available_seats = self.get_available_seats()
        logger.debug("Available seats: %s", available_seats)

        self.select_seats(available_seats, target_seat)
        self.proceed_to_fast_track()
        self.handle_add_fast_track()

    def handle_search_page(
        self, date: str, origin: str, destination: str, flight_number: str
    ):
        """Perform actions on the search page."""
        self.open_search_page(date, origin, destination)
        self.accept_cookies()

        if not self.flights_exist():
            logger.error("No flights exist with the given parameters.")
            raise Exception("No flights available.")

        flight_card = self.get_flight_card(flight_number)
        if not flight_card:
            logger.error("Could not find the specified flight.")
            raise Exception("Flight not found.")

        logger.info("Flight number %s found.", flight_number)

        if self.is_flight_sold_out(flight_card):
            logger.error("Selected flight is sold out.")
            raise Exception("Flight is sold out.")

        # Find maximum available seats
        logger.info("Finding maximum available seats.")
        flight_card = self.find_available_seats(
            date, origin, destination, flight_number
        )
        if not flight_card:
            logger.error("No available seats found.")
            raise Exception("No available seats.")

        logger.info("There are %d seats available.", self.num_passengers)

        self.select_flight(flight_card)
        self.select_fare()
        self.login_later()
        self.fill_passenger_details()
        self.proceed_to_seats_page()

    def run(
        self,
        date: str,
        origin: str,
        destination: str,
        flight_number: str,
        target_seat: str,
    ):
        """Run the bot with specified parameters."""
        try:
            self.handle_search_page(date, origin, destination, flight_number)
            self.select_seats_page(target_seat)
            logger.info("Seat reservation process completed successfully.")
        except Exception as e:
            logger.error("An error occurred during the seat reservation process: %s", e)
            raise
