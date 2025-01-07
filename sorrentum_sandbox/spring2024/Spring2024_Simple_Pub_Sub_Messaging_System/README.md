
Technical Overview and Implementation
  The essence of this project lies in three primary components: the publisher, subscriber, and
RabbitMQ message broker, each isolated within separate Docker containers. This isolation enhances
deployment ease and environmental consistency. RabbitMQ acts as the broker, orchestrating message
queues and ensuring precise message routing between publishers and subscribers.
  RabbitMQ was chosen for its comprehensive features, including support for various messaging
protocols, high availability, and adaptable routing capabilities. It is configured with a fanout exchange
that broadcasts messages to all connected queues indiscriminately, making it suitable for scenarios that
require widespread message dissemination.

RabbitMQ: Advanced Message Queuing Protocol
  RabbitMQ is a widely recognized open-source message broker software that implements the
Advanced Message Queuing Protocol (AMQP). It facilitates complex routing scenarios and ensures
message delivery even when the receiver is temporarily unavailable. RabbitMQ's reliability, scalability,
and high availability make it a staple in distributed systems and microservices architectures.
- Speed and Reliability: RabbitMQ efficiently handles high volumes of data while ensuring that
messages are reliably delivered to the correct consumer.
- Scalability: Easily scales to accommodate increased loads, which is essential for maintaining
system performance under varying loads.
- Flexibility: Supports multiple messaging protocols, message queuing, delivery acknowledgment,
and durable storage of messages.

Docker: Containerization for Portability
  Docker simplifies the deployment of applications within lightweight and portable containers.
These containers encapsulate an application with all its dependencies, ensuring consistent operation
across different computing environments, rapid deployment, and resource efficiency.
  The project leverages Docker to ensure that all components—RabbitMQ, the publisher, and the
subscriber—operate within controlled and consistent environments. This section outlines the structure
and logic behind the Docker configurations used in the project.
  To initiate the container system, use the ‘sudo docker-compose up -d –build’ command. This
command starts all the services defined in the docker-compose.yml file, including RabbitMQ, the
publisher, and the subscriber. After the containers are up, the RabbitMQ server may take approximately
150-180 seconds to become fully operational. During this time, it is preparing the environment and
setting up user credentials as specified in the init-rabbitmq.sh script.
  Once RabbitMQ is ready, navigate to http://localhost:15672 and log in with the username and
password (user). Then, we head to the ‘Queues and Steams’ section and create a few queues, we bind
the newly created queues to our exchange ‘logs’ (these will be our subscribers). This will ensure that
any message sent from the exchange logs will go to all queues that are bound to our exchange. This
allows us to test the message dissemination across all subscribers.
  The project leverages Docker to ensure that all components—RabbitMQ, the publisher, and the
subscriber—operate within controlled and consistent environments. This section outlines the structure
and logic behind the Docker configurations used in the project.

Python Script Overview
  The functionality of the pub/sub system is encapsulated in two Python scripts: publisher.py and
subscriber.py. These scripts utilize the pika library, a RabbitMQ client library that provides a robust
interface for Python applications to interact with RabbitMQ.
    - Publisher Script: Defines how messages are sent. It declares the necessary exchanges
and queues and publishes messages to the exchange.
    - Subscriber Script: Handles the consumption of messages. It subscribes to the
appropriate queue and processes incoming messages as defined in the callback function.
  In the configuration of RabbitMQ within a Dockerized environment or a typical server setup,
you will often encounter two specific ports: 5672 and 15672. Each of these ports serves a distinct
purpose in the management and operation of RabbitMQ, enabling different functionalities crucial for
both developers and system administrators.

- Port 5672: AMQP Protocol Communication
  Port 5672 is the default port used by RabbitMQ for client connections that communicate using
the Advanced Message Queuing Protocol (AMQP). AMQP is the core messaging protocol used by
RabbitMQ for messaging between the clients (producers and consumers) and the server. This port is
used for most of the standard client-server messaging operations within RabbitMQ, and for reliable
messaging and flexible routing. Clients, such as your publisher and subscriber in the Dockerized pub/sub
system, connect to RabbitMQ through this port to perform messaging operations.

- Port 15672: RabbitMQ Management Plugin
  Port 15672 is utilized by the RabbitMQ Management Plugin, serving as a crucial tool for
administrative and monitoring tasks. It provides a graphical interface that allows system administrators
and developers to interact seamlessly with the RabbitMQ server, which is invaluable for setting up
configurations, monitoring message throughput, and debugging issues. This port features a
comprehensive dashboard that displays the current state of queues, exchanges, and connections,
enables the creation, deletion, and modification of queues and exchanges directly from the web
interface, offers detailed metrics on message rates, resource usage, and errors, and facilitates robust
access control management for various parts of the RabbitMQ instance.

Project Setup
The system comprises several Docker containers, each serving a specific role:
- RabbitMQ Container: Manages all message queuing and routing functionalities.
- Publisher Container: Responsible for sending messages to the RabbitMQ broker.
- Subscriber Container: Consumes the messages dispatched through RabbitMQ.
- Dockerfiles and Docker-Compose Configuration
Dockerfile:
- The RabbitMQ container is set up using the official rabbitmq:3-management image, which
includes the management plugin.
- Publisher and Subscriber containers are built on the python:3.8-slim image, ensuring a minimal
footprint and quick deployment.
Docker-Compose:
Manages the relationship between containers, network configurations, and volume mappings as
it facilitates easy start-up and teardown of the multi-container setup with simple commands.
