FROM python:3.9

# Install Redis
RUN apt-get update && apt-get install -y redis-server

# Install redis-py
RUN pip install redis

# Expose the Redis port
FROM python:3.9

# Install Redis
RUN apt-get update && apt-get install -y redis-server

# Install redis-py
RUN pip install redis

# Expose the Redis port
EXPOSE 6379

# Set working directory
WORKDIR /app

# Copy Python script (assuming your Python script is named app.py)
COPY app.py .

# Start Redis server and run the Python script
CMD ["bash", "-c", "service redis-server start && python app.py"]

