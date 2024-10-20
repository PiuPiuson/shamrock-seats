import os
import logging
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from ryanair import Ryanair

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram bot token from environment variable
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# States for conversation
DATE, ORIGIN, DESTINATION, FLIGHT_NUMBER, SEAT = range(5)


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
        "Great! Let's start with the flight date.\n\n"
        "Please enter the flight date in the format YYYY-MM-DD:"
    )
    return DATE  # Move to the next step


async def get_flight_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the flight date and ask for the origin."""
    date_input = update.message.text.strip()
    # Validate date format
    try:
        datetime.strptime(date_input, "%Y-%m-%d")
        context.user_data["date"] = date_input
        await update.message.reply_text(
            "Got it!\n\nNow, enter the origin airport code (e.g., STN):"
        )
        return ORIGIN
    except ValueError:
        await update.message.reply_text(
            "Invalid date format. Please enter date as YYYY-MM-DD:"
        )
        return DATE


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
    """Store the destination and ask for the flight number."""
    destination_input = update.message.text.strip().upper()
    if not destination_input.isalpha() or len(destination_input) != 3:
        await update.message.reply_text(
            "Invalid airport code. Please enter a 3-letter code (e.g., ATH):"
        )
        return DESTINATION
    context.user_data["destination"] = destination_input
    await update.message.reply_text("Please enter the flight number (e.g., FR2362):")
    return FLIGHT_NUMBER


async def get_flight_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the flight number and ask for the preferred seat."""
    flight_number_input = update.message.text.strip().replace(" ", "").upper()
    if (
        not flight_number_input.startswith("FR")
        or not flight_number_input[2:].isdigit()
    ):
        await update.message.reply_text(
            "Invalid flight number. Please enter a valid Ryanair flight number (e.g., FR2362):"
        )
        return FLIGHT_NUMBER
    context.user_data["flight_number"] = flight_number_input
    await update.message.reply_text(
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
            DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_date)],
            ORIGIN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_origin)
            ],
            DESTINATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_destination)
            ],
            FLIGHT_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_flight_number)
            ],
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
