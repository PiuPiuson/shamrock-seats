import os
import logging
from datetime import datetime
import tempfile
import math
import asyncio
from functools import wraps


from proxy import Proxy


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
from telegram.constants import ChatAction

from selenium import webdriver
from selenium.webdriver.chrome.service import Service

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
PROXY_TOKEN = os.getenv("PROXY_API_KEY")
SELENIUM_URL = os.getenv("SELENIUM_URL")

# States for conversation
ORIGIN, DESTINATION, TIME, SEATS_SELECTION, CONFIRMATION = range(5)


def retry_async(exceptions, max_attempts=3, initial_delay=1, backoff_factor=2):
    """Retry decorator with exponential backoff for async functions."""

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt < max_attempts - 1:
                        logger.warning(
                            "Attempt %d failed with error: %s. "
                            "Retrying in %d seconds...",
                            attempt + 1,
                            e,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        delay *= backoff_factor
                    else:
                        logger.error(
                            "Max attempts reached for %s. Giving up.", func.__name__
                        )
                        raise

        return wrapper

    return decorator


@retry_async(
    (
        FlightNotFoundError,
        FlightSoldOutError,
        SeatsNotAvailableError,
        SeatSelectionError,
        RyanairScriptError,
    ),
    max_attempts=3,
    initial_delay=1,
    backoff_factor=1,
)
async def open_driver_and_reserve(
    proxy, origin, destination, departure_time, seats_to_reserve: list
):
    """Open a WebDriver, perform seat reservations, and handle errors."""

    driver = create_webdriver(proxy)
    ra = Ryanair(driver, origin, destination, departure_time)

    try:
        await asyncio.to_thread(ra.reserve_seats, seats_to_reserve)

    finally:
        await asyncio.to_thread(driver.quit)


def create_webdriver(proxy_ip: str = None):
    options = webdriver.ChromeOptions()
    options.add_argument("--incognito")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_experimental_option(
        "prefs", {"profile.managed_default_content_settings.images": 2}
    )
    options.add_argument("--headless=new")

    user_data_dir = tempfile.mkdtemp()
    options.add_argument(f"--user-data-dir={user_data_dir}")

    if proxy_ip:
        options.add_argument(f"--proxy-server=http://{proxy_ip}")

    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=options)

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36",
    ]

    driver.execute_cdp_cmd(
        "Network.setUserAgentOverride", {"userAgent": user_agents[0]}
    )

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.set_window_size(1280, 1280)

    return driver


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when the command /start is issued."""
    await update.message.reply_text(
        "Ah, top of the mornin' to ya! 🍀\n\n"
        "Welcome to ShamrockSeats, where you're as lucky as a four-leaf clover!\n"
        "Use /reserve to save yourself a cozy spot on the plane.\n"
        "If ya change your mind, just type /cancel and I'll sort it out."
    )


async def reserve_seat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the seat reservation conversation."""
    await update.message.reply_text(
        "Right so, let's get crackin'!\n\nGive us the 3-letter code for where you're flyin' out from (e.g., STN):"
    )
    return ORIGIN


async def get_flight_origin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the origin and ask for the destination."""
    origin_input = update.message.text.strip().upper()
    if not origin_input.isalpha() or len(origin_input) != 3:
        await update.message.reply_text(
            "Now now, that doesn't seem right. Give us a proper 3-letter code (e.g. STN):"
        )
        return ORIGIN

    context.user_data["origin"] = origin_input

    await update.message.reply_text(
        "Lovely jubbly! Now, where's your final stop? (e.g. OSL):"
    )
    return DESTINATION


async def get_flight_destination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the destination and ask for the flight date."""
    destination_input = update.message.text.strip().upper()
    if not destination_input.isalpha() or len(destination_input) != 3:
        await update.message.reply_text(
            "Oh, that doesn't look right. Could ya give us a proper 3-letter code? (e.g. OSL):"
        )
        return DESTINATION

    context.user_data["destination"] = destination_input

    await update.message.reply_text(
        "Grand! And what time does your flight take off? (e.g. 14:30)"
    )
    return TIME


def divide_seats_evenly(seats, max_rows=4):
    """Distribute the seats as evenly as possible across the rows."""
    num_seats = len(seats)
    rows = min(
        max_rows, num_seats
    )  # Limit to a max of 'max_rows' rows or total seat count

    # Calculate the number of seats per row as evenly as possible
    seats_per_row = [math.ceil(num_seats / rows)] * rows
    total_seats = sum(seats_per_row)

    # Adjust to ensure total seats match the number of available seats
    if total_seats > num_seats:
        for i in range(total_seats - num_seats):
            seats_per_row[-(i + 1)] -= 1

    # Split the seats list into rows based on seats_per_row
    seat_layout = []
    start_index = 0
    for count in seats_per_row:
        seat_layout.append(seats[start_index : start_index + count])
        start_index += count

    return seat_layout


async def get_flight_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store the flight time and ask for the seat."""
    time_input = update.message.text.strip()
    # Validate date format
    try:
        datetime.strptime(time_input, "%H:%M")
        context.user_data["time"] = time_input

    except ValueError:
        await update.message.reply_text(
            "Ah sure, that time doesn't look right. Give it another go in the format HH:MM:"
        )
        return TIME

    if not context.user_data.get("available_seats", None):
        logger.info(
            "Getting available seats for %s - %s at %s",
            context.user_data["origin"],
            context.user_data["destination"],
            context.user_data["time"],
        )

        await update.message.reply_text(
            "Hold tight, I'm checking the seats for ya... 🛫"
        )
        await update.effective_chat.send_action(ChatAction.TYPING)

        driver = create_webdriver()
        ra = Ryanair(
            driver,
            context.user_data["origin"],
            context.user_data["destination"],
            context.user_data["time"],
        )

        try:
            context.user_data["available_seats"] = ra.get_available_seats_in_flight()

        except FlightNotFoundError:
            await update.message.reply_text(
                "Ah, no luck finding that flight. Maybe try again with /reserve."
            )
            return await end_conversation(context)
        except FlightSoldOutError:
            await update.message.reply_text(
                "Oh dear, looks like the flight's as full as a pub on St. Paddy's Day! 🍻\n"
                "Try your luck another time."
            )
            return await end_conversation(context)
        except RyanairScriptError:
            await update.message.reply_text(
                "Oops! Something went a bit wonky on our end. Try again with /reserve."
            )
            return await end_conversation(context)
        finally:
            driver.quit()

    available_seats = context.user_data["available_seats"]

    logger.info("%d seats available in the flight", len(available_seats))

    if len(available_seats) == 1:
        await update.message.reply_text(
            "There's only the one seat left, so grab it quick before it disappears!"
        )
        return await end_conversation(context)

    reply_markup = create_seats_keyboard_markup(available_seats)
    await update.message.reply_text(
        "Pick a seat there now, don't be shy:", reply_markup=reply_markup
    )
    return SEATS_SELECTION


def create_seats_keyboard_markup(available_seats: list[str]):
    """Creates the markup selection for seats"""
    seat_layout = divide_seats_evenly(available_seats)

    keyboard = [
        [InlineKeyboardButton(seat, callback_data=seat) for seat in row]
        for row in seat_layout
    ]

    # Add a 'Done' button at the end to finalize the seat selection
    keyboard.append([InlineKeyboardButton("Done", callback_data="Done")])

    return InlineKeyboardMarkup(keyboard)


async def get_flight_seat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow multiple seat selection and store them."""
    query = update.callback_query
    await query.answer()

    # Retrieve the selected seat
    selected_seat = query.data

    available_seats = context.user_data.get("available_seats")
    reply_markup = create_seats_keyboard_markup(available_seats)

    # Check if the selected seat is "Done" to finish the selection
    if selected_seat == "Done":
        selected_seats = context.user_data.get("selected_seats", [])
        if not selected_seats:
            await query.edit_message_text(
                "You haven't selected any seats. Please choose at least one seat.",
                reply_markup=reply_markup,
            )
            return SEATS_SELECTION

        await query.edit_message_text(
            f"Snatching up every seat apart from {', '.join(selected_seats)}"
        )

        # Proceed to the reservation process
        return await start_reservation(update, context, selected_seats)

    # Add or remove the selected seat to the list
    selected_seats = context.user_data.setdefault("selected_seats", [])
    if selected_seat in selected_seats:
        selected_seats.remove(selected_seat)
    else:
        selected_seats.append(selected_seat)
        selected_seats.sort()

    # Update the seat selection message with the chosen seats

    selected_seats = context.user_data.get("selected_seats", [])
    await query.edit_message_text(
        f"Seats selected: {', '.join(selected_seats)}\n\n"
        "Tap a seat to pick it or put it down, or tap 'Done' when you're all set.",
        reply_markup=reply_markup,
    )


async def start_reservation(
    update: Update, context: ContextTypes.DEFAULT_TYPE, seats_to_reserve
):
    """Initiate the reservation process with the selected seats."""
    origin = context.user_data["origin"]
    destination = context.user_data["destination"]
    departure_time = context.user_data["time"]
    available_seats = context.user_data["available_seats"]

    loading_message = await update.effective_chat.send_message(
        "Right, I'm getting everything sorted for ya... ⏳"
        "It won't take but a moment or two"
    )

    await update.effective_chat.send_action(ChatAction.TYPING)

    driver = create_webdriver()
    ra = Ryanair(driver, origin, destination, departure_time)
    proxies = Proxy(PROXY_TOKEN)

    try:
        available_tickets = ra.get_number_of_tickets_available()
    except (FlightNotFoundError, FlightSoldOutError, SeatsNotAvailableError):
        await loading_message.edit_text(
            "Ah, looks like the flight info changed. Give it another whirl with /reserve."
        )
        return await end_conversation(context)
    except RyanairScriptError:
        await loading_message.edit_text(
            "Something went sideways on us. Try again with /reserve."
        )
        return await end_conversation(context)
    finally:
        driver.quit()

    await update.effective_chat.send_action(ChatAction.TYPING)

    seats_remaining = available_seats.copy()
    for seat in seats_to_reserve:
        seats_remaining.remove(seat)

    drivers_needed = math.ceil(len(seats_remaining) / available_tickets)
    logger.info("Need to create %d chrome drivers", drivers_needed)

    proxy_list = proxies.get_proxy_list()

    tasks = []

    for i in range(drivers_needed):
        num_seats_to_reserve = (
            available_tickets
            if len(seats_remaining) >= available_tickets
            else len(seats_remaining)
        )
        seats_batch = seats_remaining[:num_seats_to_reserve]

        logger.info("Session %d needs to reserve %d seats", i + 1, len(seats_batch))

        proxy = proxy_list.pop()
        seats_remaining = seats_remaining[num_seats_to_reserve:]

        tasks.append(
            open_driver_and_reserve(
                proxy, origin, destination, departure_time, seats_batch
            )
        )

    # Run all the tasks concurrently
    await asyncio.gather(*tasks)

    await loading_message.edit_text("All done! Your seats are sorted! 🎟️✨")
    await update.effective_chat.send_message(
        "Time to check in with random seat allocation and get yourself sorted. Safe travels! 🛫"
    )
    return await end_conversation(context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current conversation."""
    await update.message.reply_text(
        "Ah, no worries at all. I've canceled your seat reservation. Take care, now!"
    )
    return await end_conversation(context)


async def end_conversation(context):
    """Clear user context at the end of the conversation"""
    context.user_data.clear()

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
            SEATS_SELECTION: [CallbackQueryHandler(get_flight_seat)],
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
