


from flask import Flask, request
import pika
import json

app = Flask(__name__)

def get_channel():
    connection_parameters = pika.ConnectionParameters(
        host='my-rabbit',
        credentials=pika.PlainCredentials('user', 'user')
    )
    connection = pika.BlockingConnection(connection_parameters)
    return connection.channel()

@app.route('/send', methods=['POST'])
def send_message():
    message = request.json.get('message')
    channel = get_channel()
    channel.basic_publish(
        exchange='logs',
        routing_key='',
        body=message,
        properties=pika.BasicProperties(delivery_mode=2)
    )
    channel.close()
    return json.dumps({'status': 'Message sent'}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)