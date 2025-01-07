import pika

def setup_exchange_and_queue():
    connection_parameters = pika.ConnectionParameters(
        host='my-rabbit',
        credentials=pika.PlainCredentials('user', 'user')
    )
    connection = pika.BlockingConnection(connection_parameters)
    channel = connection.channel()

    # Declare the fanout exchange for logs
    channel.exchange_declare(exchange='logs', exchange_type='fanout', durable=True)

    # Declare the direct exchange and queue for acknowledgments
    channel.exchange_declare(exchange='ack_exchange', exchange_type='direct', durable=True)
    ack_queue_name = "ack_queue"
    channel.queue_declare(queue=ack_queue_name, durable=True)
    channel.queue_bind(exchange='ack_exchange', queue=ack_queue_name)

    connection.close()

if __name__ == '__main__':
    setup_exchange_and_queue()
