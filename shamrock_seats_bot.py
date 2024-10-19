import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackContext,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
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

# Store user flight details in a dictionary
user_data = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    await update.message.reply_text(
        "Welcome to ShamrockSeats! 🍀 Use /reserve to reserve a selected seat."
    )


async def reserve_seat_start(update: Update, context: CallbackContext):
    """Start the seat reservation conversation."""
    await update.message.reply_text(
        "Great! Let's start with the flight date. Please enter the flight date (YYYY-MM-DD):"
    )
    return DATE  # Move to the next step


async def get_flight_date(update: Update, context: CallbackContext):
    """Store the flight date and ask for the origin."""
    user_data["date"] = update.message.text
    await update.message.reply_text(
        "Got it! Now, enter the origin airport code (e.g., STN):"
    )
    return ORIGIN


async def get_flight_origin(update: Update, context: CallbackContext):
    """Store the origin and ask for the destination."""
    user_data["origin"] = update.message.text
    await update.message.reply_text(
        "Thanks! Now, enter the destination airport code (e.g., ATH):"
    )
    return DESTINATION


async def get_flight_destination(update: Update, context: CallbackContext):
    """Store the destination and ask for the flight number."""
    user_data["destination"] = update.message.text
    await update.message.reply_text("Please enter the flight number (e.g., FR2362):")
    return FLIGHT_NUMBER


async def get_flight_number(update: Update, context: CallbackContext):
    """Store the flight number and ask for the preferred seat."""
    user_data["flight_number"] = update.message.text
    await update.message.reply_text(
        "Almost done! Please enter your preferred seat (e.g., 01C):"
    )
    return SEAT


async def get_flight_seat(update: Update, context: CallbackContext):
    """Store the seat number and proceed to reserve the seat."""
    user_data["seat"] = update.message.text
    await update.message.reply_text(
        f"Got it! Reserving seat {user_data['seat']} on flight {user_data['flight_number']} "
        f"from {user_data['origin']} to {user_data['destination']} on {user_data['date']}..."
    )

    # Use Selenium to reserve the seat
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
    ra = Ryanair(driver)

    try:
        ra.run(
            user_data["date"],
            user_data["origin"],
            user_data["destination"],
            user_data["flight_number"],
            user_data["seat"],
        )
        await update.message.reply_text("Success! You should book now!")
    except Exception as e:
        logger.error(f"Error during seat reservation: {e}")
        await update.message.reply_text(
            "Oops, something went wrong while reserving your seat!"
        )
    finally:
        driver.quit()

    return ConversationHandler.END  # End the conversation


async def cancel(update: Update, context: CallbackContext):
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
