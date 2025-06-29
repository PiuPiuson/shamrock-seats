# ShamrockSeatsBot

**ShamrockSeatsBot** is a Telegram bot that helps you reserve a random seat on a Ryanair flight if your flight is within the next 24 hours and has available seats. The bot interacts with the Ryanair website to check availability and make random seat reservations.

## Features

- Reserve a seat on a Ryanair flight (subject to availability and check-in being open within 24 hours).
- Easy-to-use interface on Telegram.
- Progress indicator during the reservation process.
- Automatic retries for common reservation errors.

## Bot Usage on Telegram

To interact with ShamrockSeatsBot on Telegram, search for **ShamrockSeatsBot** and start a conversation. Use the command `/reserve` to begin the seat reservation process.

### Environment Variables

- `TELEGRAM_BOT_TOKEN`: Telegram bot token for authentication.
- `PROXY_API_KEY`: API key for `webshare.io`.

## Setup and Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ShamrockSeatsBot.git
cd ShamrockSeatsBot
```

### 2. Set Up Environment Variables

Create a `.env` file with the following variables:

```plaintext
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
PROXY_API_KEY=your_proxy_api_key
```

### 3. Running the Bot

`docker-compose up`

### Local Development (visible browser)

If you want to run the bot **outside Docker** and actually watch Selenium controlling Chrome (useful while debugging), use the helper script `run_local.sh` that lives at the project root.

#### 1. Install prerequisites (macOS via Homebrew)

```bash
brew install --cask google-chrome   # the browser itself
brew install chromedriver           # the driver binary Selenium talks to
```

> Tip: if you use another package manager or OS, just make sure `chrome` / `google-chrome` and `chromedriver` are on your `PATH`.

#### 2. Create / update your `.env`

Same as the Docker setup, but you can keep extra variables here as well:

```dotenv
TELEGRAM_BOT_TOKEN=...   # required
PROXY_API_KEY=...        # required
```

`run_local.sh` automatically sources this file and exports the variables.

#### 3. Start the bot

```bash
./run_local.sh             # forwards any extra CLI args to python bot/bot.py
```

The script sets `HEADLESS=0`, autodetects `chromedriver` if not already defined, and launches `python bot/bot.py`. A real Chrome window should pop up so you can see what Selenium is doing.

## Usage

### Commands

- **`/start`**: Start the bot and see a welcome message.
- **`/reserve`**: Begin the seat reservation process.
- **`/cancel`**: Cancel the current reservation process at any time.

### Reservation Process

1. **Start** the reservation with `/reserve`.
2. **Enter flight details**: Origin airport code, destination airport code, and flight time.
3. **Select a seat**: Choose from available seats on the flight.
4. **Wait for confirmation**: The bot will attempt to reserve every other seat apart from the selected one.
5. **Completion**: Once seats are reserved, the bot confirms the reservation.

## Code Overview

- **`create_webdriver`**: Configures Selenium WebDriver with proxy support and headless mode if needed.
- **`reserve_seat_start`**: Initializes the reservation process by collecting origin, destination, and time inputs.
- **`get_flight_seat`**: Displays available seats for selection and initiates the reservation.
- **Error Handling**: Catches various errors like `FlightNotFoundError`, `FlightSoldOutError`, and retries reservations as needed.