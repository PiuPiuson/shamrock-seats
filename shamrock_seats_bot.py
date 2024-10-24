import os
import logging
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler,
)

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

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# States for conversation
ORIGIN, DESTINATION, TIME, FLIGHT_NUMBER, SEAT = range(5)


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to ShamrockSeats! 🍀\n\n"
        "Use /reserve to reserve a selected seat.\n\n"
        "You can cancel at any time by typing /cancel"
    )


async def reserve_seat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the seat reservation conversation."""
    await update.message.reply_text(
        "Great! Let's start!\n\n Please enter the origin airport code (e.g., STN):"
    )
    return ORIGIN


async def get_flight_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the origin and ask for the destination."""
    origin_input = update.message.text.strip().upper()
    if not origin_input.isalpha() or len(origin_input) != 3:
        await update.message.reply_text(
            "Invalid airport code. Please enter a 3-letter code (e.g., STN):"
        )
        return ORIGIN

    context.user_data["origin"] = origin_input

    await update.message.reply_text(
        "Thanks!\n\nNow, enter the destination airport code (e.g., ATH):"
    )
    return DESTINATION


async def get_flight_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the destination and ask for the flight date."""
    destination_input = update.message.text.strip().upper()
    if not destination_input.isalpha() or len(destination_input) != 3:
        await update.message.reply_text(
            "Invalid airport code. Please enter a 3-letter code (e.g., ATH):"
        )
        return DESTINATION

    context.user_data["destination"] = destination_input

    await update.message.reply_text("What time is the flight? (eg. 14:30)")
    return TIME


async def get_flight_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the flight time and ask for the seat."""
    time_input = update.message.text.strip()
    # Validate date format
    try:
        datetime.strptime(time_input, "%H:%M")
        context.user_data["time"] = time_input

    except ValueError:
        await update.message.reply_text(
            "Invalid date format. Please enter time as HH:MM:"
        )
        return TIME

    await update.message.reply_text("Looking for flight. Please wait...")

    driver = create_webdriver()
    ra = Ryanair(
        driver,
        context.user_data["origin"],
        context.user_data["destination"],
        context.user_data["time"],
    )

    try:
        available_seats = ra.get_available_seats_in_flight()
    except FlightNotFoundError:
        await update.message.reply_text("Could not find flight.\nPlease try again")
        return ConversationHandler.END
    except FlightSoldOutError:
        await update.message.reply_text(
            "Flight is sold out.\n"
            "At least one free ticket is needed for this bot to work.\n"
            "Better luck next time!"
        )
        return ConversationHandler.END
    except RyanairScriptError:
        await update.message.reply_text(
            "An internal error occurred.\nPlease try again."
        )
        return ConversationHandler.END
    finally:
        driver.quit()

    await update.message.reply_text(available_seats)
    return SEAT


async def get_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the flight date and ask for the preferred seat."""
    query = update.callback_query
    await query.answer()

    context.user_data["date"] = query.data

    await query.edit_message_text("Looking for flight. Please wait...")

    driver = create_webdriver()
    ra = Ryanair(
        driver,
        context.user_data["origin"],
        context.user_data["destination"],
        context.user_data["time"],
    )

    await query.edit_message_text(
        "Almost done!\n\nPlease enter your preferred seat (e.g., 01C):"
    )
    return SEAT


async def get_flight_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the seat number and proceed to reserve the seat."""
    seat_input = update.message.text.strip().upper()
    # Simple validation
    if (
        len(seat_input) < 2
        or not seat_input[:-1].isdigit()
        or not seat_input[-1].isalpha()
    ):
        await update.message.reply_text(
            "Invalid seat format. Please enter seat as row number followed by seat letter (e.g., 01C):"
        )
        return SEAT
    context.user_data["seat"] = seat_input
    await update.message.reply_text(
        "Got it!\n\nReserving seat %s on flight %s from %s to %s on %s..."
        % (
            context.user_data["seat"],
            context.user_data["flight_number"],
            context.user_data["origin"],
            context.user_data["destination"],
            context.user_data["date"],
        )
    )
    # Proceed to reserve seat
    await reserve_seat(update, context)
    return ConversationHandler.END  # End the conversation


async def reserve_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reserve the seat using Selenium."""
    user_data = context.user_data
    date = user_data["date"]
    origin = user_data["origin"]
    destination = user_data["destination"]
    flight_number = user_data["flight_number"]
    seat = user_data["seat"]

    # Inform user that the process may take some time
    await update.message.reply_text("Processing your request, please wait...")

    # Use Selenium to reserve the seat
    try:
        # Initialize webdriver
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
        ra = Ryanair(driver)
        ra.run(date, origin, destination, flight_number, seat)
        await update.message.reply_text(
            "Success! Seat reservation process completed.\nCheck in with random seat allocation in the next 2 minutes!"
        )
    except Exception as e:
        logger.error("Error during seat reservation: %s", e)
        await update.message.reply_text(str(e))
    finally:
        driver.quit()


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    await update.message.reply_text("Seat reservation has been canceled.")
    return ConversationHandler.END


if __name__ == "__main__":
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Define the conversation handler with the states
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("reserve", reserve_seat_start)],
        states={
            ORIGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_origin)
            ],
            DESTINATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_destination)
            ],
            TIME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_time)],
            SEAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_seat)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel)
        ],  # Allows user to cancel at any time
    )

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    # Run the bot
    application.run_polling()
