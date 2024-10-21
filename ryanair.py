import logging
import random
import string
import time
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
from selenium.webdriver.common.action_chains import ActionChains

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Ryanair:
    __TIMEOUT = 40  # Timeout for WebDriverWait

    def __init__(
        self,
        driver: WebDriver,
        date: str,
        origin: str,
        destination: str,
        flight_number: str,
    ):
        self.__driver = driver
        self.__num_passengers = 7

        self.__date = date
        self.__origin = origin
        self.__destination = destination
        self.__flight_number = flight_number

    @staticmethod
    def __generate_random_string(length: int = 6) -> str:
        """Generate a random string of specified length."""
        return "".join(random.choices(string.ascii_letters, k=length))

    def __generate_search_url(self, people: int = 1) -> str:
        """Generate the URL to search flights. Date should be 'YYYY-MM-DD'."""
        base_url = "https://www.ryanair.com/gb/en/trip/flights/select"
        params = (
            f"?adults={people}"
            f"&teens=0&children=0&infants=0"
            f"&dateOut={self.__date}"
            f"&originIata={self.__origin}"
            f"&destinationIata={self.__destination}"
            f"&isReturn=false"
            f"&discount=0"
            f"&promoCode="
            f"&isConnectedFlight=false"
        )
        return base_url + params

    def __accept_cookies(self):
        """Accept cookies on the website."""
        try:
            accept_button = WebDriverWait(self.__driver, self.__TIMEOUT).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, '[data-ref="cookie.no-thanks"]')
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

    def __flights_exist(self) -> bool:
        """Check if flights exist with the given parameters."""
        try:
            WebDriverWait(self.__driver, self.__TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".flight-card"))
            )
            logger.info("Flights are available.")
            return True
        except TimeoutException:
            logger.info("No flights found.")
            return False

    def __get_flight_card(self):
        """Retrieve the flight card element matching the flight number."""
        try:
            flight_cards = WebDriverWait(self.__driver, self.__TIMEOUT).until(
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
                    if flight_number_text == self.__flight_number:
                        return card
                except NoSuchElementException:
                    continue
            logger.warning("Flight number %s not found.", self.__flight_number)
            return None
        except TimeoutException:
            logger.error("Timeout while searching for flight cards.")
            return None

    def __is_flight_sold_out(self, flight_card) -> bool:
        """Check if a flight is sold out."""
        try:
            flight_card.find_element(
                By.CSS_SELECTOR, "flights-lazy-sold-out-flight-card"
            )
            return True
        except NoSuchElementException:
            return False

    def __make_gender_dropdown_selection(self, passenger_card):
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

    def __populate_passenger_form(self, passenger_card):
        """Populate the name and surname fields with random data."""
        try:
            inputs = passenger_card.find_elements(
                By.CSS_SELECTOR, "input[name*='form.passengers.']"
            )
            for i in inputs:
                i.send_keys(self.__generate_random_string())
        except NoSuchElementException as e:
            logger.error("Error populating name form: %s", e)
            raise

    def __open_search_page(self, people: int = 1):
        """Open the search page with the given parameters."""
        search_url = self.__generate_search_url(people)
        self.__driver.get(search_url)

    def __find_max_tickets_available(self):
        """Find the maximum number of available seats for the specified flight."""
        while self.__num_passengers > 0:
            self.__open_search_page(self.__num_passengers)
            flight_card = self.__get_flight_card()
            if not flight_card:
                logger.error("Could not find the specified flight.")
                return None
            if self.__is_flight_sold_out(flight_card):
                self.__num_passengers -= 1
                logger.info("Reducing passenger count to %d", self.__num_passengers)
            else:
                logger.info(
                    "Found available seats for %d passengers.", self.__num_passengers
                )
                return flight_card
        logger.error("No available seats found.")
        return None

    def __select_flight(self, flight_card):
        """Select the specified flight."""
        try:
            select_button = WebDriverWait(flight_card, self.__TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".flight-card-summary__select-btn")
                )
            )

            select_button.click()
            logger.info("Selected the flight.")
        except (NoSuchElementException, ElementClickInterceptedException) as e:
            logger.error("Error selecting flight: %s", e)
            raise

    def __select_fare(self):
        """Select the recommended fare."""
        try:
            recommended_fare = WebDriverWait(self.__driver, self.__TIMEOUT).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, ".fare-table__recommended-tag")
                )
            )

            actions = ActionChains(self.__driver)
            actions.move_to_element(recommended_fare).move_by_offset(
                50, 20
            ).click().perform()

            # recommended_fare.click()
            logger.info("Selected recommended fare.")
        except (
            TimeoutException,
            NoSuchElementException,
            ElementClickInterceptedException,
        ) as e:
            logger.error("Error selecting fare: %s", e)
            raise

    def __select_login_later(self):
        """Proceed without logging in."""
        try:
            login_later_button = WebDriverWait(self.__driver, self.__TIMEOUT).until(
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

    def __fill_passenger_details(self):
        """Fill in passenger details."""
        try:
            passenger_forms = WebDriverWait(self.__driver, self.__TIMEOUT).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".passenger"))
            )
            passenger_forms_data_ref = [
                form.get_attribute("data-ref") for form in passenger_forms
            ]

            for data_ref in passenger_forms_data_ref:
                form = self.__driver.find_element(
                    By.CSS_SELECTOR, f'div[data-ref="{data_ref}"]'
                )
                self.__make_gender_dropdown_selection(form)
                self.__populate_passenger_form(form)
            logger.info("Populated passenger details.")
        except (TimeoutException, NoSuchElementException) as e:
            logger.error("Error filling passenger details: %s", e)
            raise

    def __proceed_to_seats_page(self):
        """Click on the continue button to proceed to seats page."""
        try:
            continue_button = WebDriverWait(self.__driver, self.__TIMEOUT).until(
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

    def __proceed_to_fast_track(self):
        """Click on the continue button to proceed to fast track selection."""
        try:
            continue_button = WebDriverWait(self.__driver, self.__TIMEOUT).until(
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

    def __wait_for_seatmap(self):
        """Wait until the seatmap is loaded."""
        try:
            WebDriverWait(self.__driver, self.__TIMEOUT).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".seatmap__seat"))
            )
            logger.info("Seatmap is loaded.")
        except TimeoutException as e:
            logger.error("Seatmap did not load in time: %s", e)
            raise

    def __get_available_seats_from_seatmap(self) -> List[str]:
        """Get a list of available seat IDs."""
        seats = self.__driver.find_elements(
            By.CSS_SELECTOR, ".seatmap__seat:not([class*='unavailable'])"
        )
        available_seats = []
        for seat in seats:
            seat_id = seat.get_attribute("id")
            if seat_id:
                available_seats.append(seat_id)

        return [seat.replace("seat-", "") for seat in available_seats]

    def __select_seats(self, seats: list[str]):
        """Select seats from seatmap"""

        for seat in seats:
            seat_id = f"seat-{seat}"
            try:
                seat_element = self.__driver.find_element(
                    By.CSS_SELECTOR, f"#{seat_id}"
                )
                self.__driver.execute_script("arguments[0].click();", seat_element)
                logger.info("Selected seat %s", seat)
            except NoSuchElementException as e:
                logger.error("Error selecting seat %s: %s", seat_id, e)
                raise

    def __handle_add_fast_track(self):
        """Handle the fast track page."""
        try:
            add_fast_track_button = WebDriverWait(self.__driver, self.__TIMEOUT).until(
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

    def get_available_seats_in_flight(self):
        """Returns a list of all available seats in a flight"""
        self.__open_search_page(1)
        logger.info("Opened search page.")
        self.__accept_cookies()

        if not self.__flights_exist():
            logger.error("No flights exist with the given parameters.")
            raise Exception("No flights available.")

        flight_card = self.__get_flight_card()
        if not flight_card:
            logger.error("Could not find the specified flight.")
            raise Exception("Flight not found.")

        logger.info("Flight number %s found.", self.__flight_number)

        if self.__is_flight_sold_out(flight_card):
            logger.error("Selected flight is sold out.")
            raise Exception("Flight is sold out.")

        self.__select_flight(flight_card)
        self.__select_fare()
        self.__select_login_later()
        self.__fill_passenger_details()
        self.__proceed_to_seats_page()

        self.__wait_for_seatmap()

        available_seats = self.__get_available_seats_from_seatmap()
        logger.debug("Available seats: %s", available_seats)

        return available_seats

    def get_number_of_tickets_available(self):
        """Returns the number of available tickets in a flight (can be used to select that many seats at once)"""
        self.__open_search_page(1)
        logger.info("Opened search page.")
        self.__accept_cookies()

        # Find maximum available tickets
        logger.info("Finding maximum available tickets.")
        flight_card = self.__find_max_tickets_available()
        if not flight_card:
            logger.error("No available seats found.")
            raise Exception("No available seats.")

        logger.info("There are %d seats available.", self.__num_passengers)
        return self.__num_passengers

    def reserve_seats(self, seats: list):
        """Reserves a list of seats from the flight"""
        self.__open_search_page(len(seats))
        logger.info("Opened search page.")
        self.__accept_cookies()

        if not self.__flights_exist():
            logger.error("No flights exist with the given parameters.")
            raise Exception("No flights available.")

        flight_card = self.__get_flight_card()
        if not flight_card:
            logger.error("Could not find the specified flight.")
            raise Exception("Flight not found.")

        logger.info("Flight number %s found.", self.__flight_number)

        if self.__is_flight_sold_out(flight_card):
            logger.error("Selected flight is sold out.")
            raise Exception("Flight is sold out.")

        self.__select_flight(flight_card)
        self.__select_fare()
        self.__select_login_later()
        self.__fill_passenger_details()
        self.__proceed_to_seats_page()

        self.__wait_for_seatmap()
        available_seats = self.__get_available_seats_from_seatmap()

        if not all(elem in available_seats for elem in seats):
            raise Exception(
                f"Seat(s) {[elem for elem in available_seats if elem not in seats]} aren't available"
            )

        self.__select_seats(seats)
        self.__proceed_to_fast_track()
        self.__handle_add_fast_track()

    def __click_ryanair_logo(self):
        """Clicks the ryanair logo on the top left of the page"""
        self.__driver.find_element(By.CSS_SELECTOR, ".common-header__logo-icon").click()

    def free_reserved_seats(self):
        """Frees seats reserved in this session"""
        logger.info("Freeing seats up")
        self.__click_ryanair_logo()
        self.__open_search_page()
        time.sleep(5)
        logger.info("Seats freed successfully")
