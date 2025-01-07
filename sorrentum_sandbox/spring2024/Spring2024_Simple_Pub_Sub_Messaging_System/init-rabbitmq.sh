
#!/bin/bash

# Wait until RabbitMQ is fully operational
echo "Waiting for RabbitMQ to start..."
rabbitmqctl wait --timeout 20 $RABBITMQ_PID_FILE

# Add a new user and set permissions
echo "Configuring RabbitMQ user..."
rabbitmqctl add_user $RABBITMQ_DEFAULT_USER $RABBITMQ_DEFAULT_PASS
rabbitmqctl set_user_tags $RABBITMQ_DEFAULT_USER administrator
rabbitmqctl set_permissions -p / $RABBITMQ_DEFAULT_USER ".*" ".*" ".*"

echo "*** User '$RABBITMQ_DEFAULT_USER' with password '$RABBITMQ_DEFAULT_PASS' completed. ***"
echo "*** Log in the WebUI at port 15672 (example: http://localhost:15672) ***"

exec rabbitmq-server $@
