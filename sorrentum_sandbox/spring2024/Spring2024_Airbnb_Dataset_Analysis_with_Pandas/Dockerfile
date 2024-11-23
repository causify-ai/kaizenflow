# Base Image
FROM python:3.9-slim

# Set the Working Directory
WORKDIR /app

# Copy local code to the container
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir pandas matplotlib

# Install tkinter for GUI support
RUN apt-get update && apt-get install -y tk \
    && rm -rf /var/lib/apt/lists/*

# Command to run on container start
CMD ["python", "./FinalProject/KayiWong605.py"]