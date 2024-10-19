# Dockerfile

# Use an official Python image as the base
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose the necessary port for the bot (optional)
EXPOSE 8080

# Run the bot script
CMD ["python", "shamrock_seats_bot.py"]