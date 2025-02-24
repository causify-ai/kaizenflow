# Use an official ZooKeeper image as a base
FROM zookeeper:3.7.0

# Install Python and other dependencies
RUN apt-get update && apt-get install -y python3 python3-pip

# Install Kazoo library
RUN pip3 install kazoo jupyter

# Set the working directory
WORKDIR /app

# Copy the application code into the container
COPY . /app

# Expose ZooKeeper default port
EXPOSE 2181

# Start ZooKeeper server
CMD ["zkServer.sh", "start-foreground"]
