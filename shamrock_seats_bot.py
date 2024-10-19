import os
import logging
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SELENIUM_URL = os.getenv("SELENIUM_URL")


# Selenium setup to connect to the Selenium container
def get_webdriver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # Connect to the Selenium container running standalone Chrome
    return webdriver.Remote(
        command_executor=SELENIUM_URL,
        desired_capabilities=DesiredCapabilities.CHROME,
        options=options,
    )


def start(update: Update, context: CallbackContext):
    """Send a message when the command /start is issued."""
    update.message.reply_text(
        "Welcome to ShamrockSeats! 🍀 Please send me your flight details."
    )


def reserve_seat(update: Update, context: CallbackContext):
    """Reserve a seat using Selenium."""
    chat_id = update.message.chat_id
    update.message.reply_text(f"Hold on, I'm grabbing you the best seat... 🍀")

    # Example: Using Selenium to interact with a Ryanair flight page
    driver = get_webdriver()
    try:
        driver.get("https://www.ryanair.com")
        # Example code to interact with the Ryanair website and reserve a seat
        # driver.find_element(By.ID, 'flight-search-input').send_keys('Your flight details here')

        # Simulate seat reservation process with Selenium
        seat_reserved = "1A"  # Mocking the seat reservation
        update.message.reply_text(f"Success! You have reserved seat {seat_reserved}. ✈️")
    except Exception as e:
        logger.error(f"Error during seat reservation: {e}")
        update.message.reply_text(
            "Oops, something went wrong while reserving your seat!"
        )
    finally:
        driver.quit()


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reserve", reserve_seat))

    # Run the bot
    application.run_polling()
