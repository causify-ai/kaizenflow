
import pika
import time

def connect_to_rabbitmq(parameters, retry_delay=10, max_retries=10):
    for attempt in range(max_retries):
        try:
            return pika.BlockingConnection(parameters)
        except pika.exceptions.AMQPConnectionError as error:
            print(f"Attempt {attempt + 1}: Connection failed, error: {error}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Failed to connect to RabbitMQ after several attempts.")
                raise

def callback(ch, method, properties, body):
    print(f"Subscriber received message: {body}")
    # Manually send the acknowledgement after processing the message
    time.sleep(5)  # delay for testing visibility
    ch.basic_ack(delivery_tag=method.delivery_tag)

def main():
    connection_parameters = pika.ConnectionParameters(
        host='my-rabbit',
        credentials=pika.PlainCredentials('user', 'user')
    )

    connection = connect_to_rabbitmq(connection_parameters)
    channel = connection.channel()

    # Declare the fanout exchange for logs
    channel.exchange_declare(exchange='logs', exchange_type='fanout', durable=True)

    # Declare a queue with RabbitMQ assigned name, without exclusive flag
    result = channel.queue_declare(queue='', durable=True)
    queue_name = result.method.queue

    # Bind the queue to the 'logs' exchange
    channel.queue_bind(exchange='logs', queue=queue_name)

    # Set prefetch count
    channel.basic_qos(prefetch_count=1)

    print(f' [*] Waiting for logs in queue {queue_name}. To exit press CTRL+C')
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    channel.start_consuming()

if __name__ == '__main__':
    main()


