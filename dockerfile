# Use an official Python image as the base
FROM python:3.12.5

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Update apt-get
RUN apt-get update

# Install Chrome
RUN curl -LO https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb && \
    apt-get install -y ./google-chrome-stable_current_amd64.deb && \
    rm google-chrome-stable_current_amd64.deb

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Start the bot script
CMD ["python", "shamrock_seats_bot.py"]