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