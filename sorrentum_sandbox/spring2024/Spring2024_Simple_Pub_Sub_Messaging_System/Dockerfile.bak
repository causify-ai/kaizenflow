# Use Python base image
FROM python:3.9-slim

# Set working directory inside the container
WORKDIR /app

# Install system packages (including pip)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy publisher and subscriber scripts into the container
COPY publisher.py .
COPY subscriber.py .

# Command to run the publisher script by default
CMD ["python", "publisher.py"]
