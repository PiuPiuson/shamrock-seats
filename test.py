from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

import random
import string

from webdriver_manager.chrome import ChromeDriverManager
import time


def generate_random_string():
    # Generate a random string of 3 to 7 characters
    length = random.randint(3, 7)
    return "".join(random.choices(string.ascii_letters, k=length))


# Set up the Chrome WebDriver using WebDriver Manager to install ChromeDriver automatically
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))


def generate_search_url(date: str, origin: str, destination: str, people=1):
    """Generate the url to search flights. Date should be 'YYYY-MM-DD'"""
    return f"https://www.ryanair.com/gb/en/trip/flights/select?adults={people}&teens=0&children=0&infants=0&dateOut={date}&dateIn=&isConnectedFlight=false&discount=0&promoCode=&isReturn=false&originIata={origin}&destinationIata={destination}&tpAdults={people}&tpTeens=0&tpChildren=0&tpInfants=0&tpStartDate={date}&tpEndDate=&tpDiscount=0&tpPromoCode=&tpOriginIata={origin}&tpDestinationIata={destination}"


def get_flight_card(flight_number: str):
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".card-flight-num__content"))
    )

    # Find all flight number containers
    flight_number_containers = driver.find_elements(
        By.CSS_SELECTOR, ".card-flight-num__content"
    )

    if len(flight_number_containers) == 0:
        print("No flight number containers found.")
        return None

    # Iterate over each flight number container
    for flight_container in flight_number_containers:
        # Check if the flight number matches the given parameter
        if flight_container.text.strip().replace(" ", "") == flight_number:
            print(f"Flight number {flight_number} found.")

            # Find the closest '.flight-card__header' element
            parent_element = flight_container.find_element(
                By.XPATH, "./ancestor::*[contains(@class, 'flight-card')]"
            )
            if parent_element:
                print("Found the corresponding flight card header.")
                return parent_element
            else:
                print("No matching flight card header found near the flight number.")
                return None

    # If no flight number matches
    print(f"Flight number {flight_number} not found on the page.")
    return None


def accept_cookies():
    try:
        # Wait up to 5 seconds for the cookie button to appear and be clickable
        WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable(
                (By.CSS_SELECTOR, '[data-ref="cookie.accept-all"]')
            )
        )
        # Locate the button and click it
        accept_button = driver.find_element(
            By.CSS_SELECTOR, '[data-ref="cookie.accept-all"]'
        )
        accept_button.click()
        print("Cookie acceptance button clicked successfully.")
    except (TimeoutException, NoSuchElementException):
        print("Cookie acceptance button not found or not clickable within 5 seconds.")


def flights_exist():
    try:
        driver.find_element(By.CSS_SELECTOR, ".no-flights")
        return False
    except NoSuchElementException:
        return True


def make_gender_dropdown_selection():
    try:
        # Wait for the dropdown button to be clickable and click it
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (
                    By.CSS_SELECTOR,
                    'ry-dropdown[data-ref="pax-details__title"] button.dropdown__toggle',
                )
            )
        ).click()

        # Wait for the "Mr" option to appear and be clickable
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "ry-dropdown-item"))
        ).click()

        print("Successfully selected 'Mr' from the gender dropdown.")

    except TimeoutException:
        print("Timeout: The dropdown or 'Mr' option did not appear.")
    except NoSuchElementException as e:
        print(f"An error occurred: {e}")


def populate_name_form():
    name_input_box = driver.find_element(
        By.CSS_SELECTOR, "input[name='form.passengers.ADT-0.name']"
    )
    random_string = generate_random_string()
    name_input_box.send_keys(random_string)

    surname_input_box = driver.find_element(
        By.CSS_SELECTOR, "input[name='form.passengers.ADT-0.surname']"
    )
    random_string = generate_random_string()
    surname_input_box.send_keys(random_string)


def first_page():
    # Open Ryanair's website
    driver.get(generate_search_url("2024-10-26", "STN", "KRK"))

    accept_cookies()

    if not flights_exist():
        print("No flights exist with those parameters")
        return

    flight_card = get_flight_card("FR2432")
    if flight_card is None:
        print("Could not find flight")
        return

    select_button = flight_card.find_element(
        By.CSS_SELECTOR, ".flight-card-summary__select-btn"
    )
    select_button.click()

    WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".fare-table__fare-column-border--recommended")
        )
    ).click()

    WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".login-touchpoint__login-later"))
    ).click()

    make_gender_dropdown_selection()
    populate_name_form()

    driver.find_element(By.CSS_SELECTOR, ".continue-flow__button").click()


def second_page(target_seat: str):
    """target_seat must be in format 02F"""
    WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, ".seatmap__seat"))
    )

    available_seat_elements = driver.find_elements(
        By.CSS_SELECTOR, ".seatmap__seat:not([class*='unavailable'])"
    )

    available_seats = [
        seat.get_attribute("id")
        for seat in available_seat_elements
        if seat.get_attribute("id").strip()
    ]

    target_seat_id = f"seat-{target_seat}"
    available_seats.remove(target_seat_id)

    if len(available_seats) == 0:
        print("All other available seats have been selected")

    selected_seat = available_seats[0]
    print(f"Selecting seat {selected_seat}")

    # Use JS to click seat as page scrolls automatically
    seat_element = driver.find_element(By.CSS_SELECTOR, f"#{selected_seat}")
    driver.execute_script("arguments[0].click();", seat_element)

    # Click continue
    driver.find_element(By.CSS_SELECTOR, ".passenger-carousel__cta--next").click()

    # Add fast track
    WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable(
            (By.CSS_SELECTOR, ".enhanced-takeover-beta__product-confirm-cta")
        )
    ).click()


if __name__ == "__main__":
    first_page()
    second_page("01A")
    time.sleep(50)

    driver.quit()
