import time
import json
from confluent_kafka import Producer
import random
import threading

# Kafka broker address
bootstrap_servers = 'kafka:9092'
# Kafka topic to publish messages to
topic = 'weather_data'

# Function to generate a random sensor value
def generate_sensor_value(min, max):
    return round(random.uniform(min, max), 2)

# Function to generate a message from each device
def generate_message(client_id):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    message = {
        'client': client_id,
        'ts': timestamp,
        'temperature': generate_sensor_value(0, 35),
        'humidity': generate_sensor_value(40, 90)
    }
    return json.dumps(message)

# Function to publish messages to Kafka topic
def publish_message(producer, topic, message):
    producer.produce(topic, message.encode('utf-8'))
    producer.flush()

# Function to publish messages for a device
def publish_device_data(client_id, frequency, producer):
    while True:
        message = generate_message(client_id)
        publish_message(producer, topic, message)
        print("Message published:", message)
        time.sleep(frequency)

# Main function
def main():
    # Kafka producer configuration
    conf = {
        'bootstrap.servers': bootstrap_servers
    }
    
    # Create Kafka producer
    producer = Producer(conf)
    
    # Dictionary of client IDs and their corresponding publishing frequencies
    client_frequencies = {
        'device1': 2,
        'device2': 5,
        'device3': 10
    }
    
    # Create a thread for each device
    threads = []
    for client_id, frequency in client_frequencies.items():
        thread = threading.Thread(target=publish_device_data, args=(client_id, frequency, producer))
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to finish
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    main()
