FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Install dependencies including Chrome and ChromeDriver
RUN apt-get update && apt-get install -y \
    chromium-driver \
    chromium \
    curl \
    gnupg \
    unzip \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file and install dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application files into the container
COPY ./bot /app

# Expose the necessary port for Selenium server (default: 4444)
EXPOSE 4444

# Run the bot script
CMD ["python", "bot/bot.py"]