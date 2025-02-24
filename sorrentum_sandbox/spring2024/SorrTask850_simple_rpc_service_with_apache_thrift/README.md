# Simple RPC Service with Apache Thrift

## Author info

- Author: Alvino Angelo
- GitHub account: aangelo09
- UMD email: aangelo@umd.edu

# Description

This Python-based project demonstrates the integration of Apache Thrift and Redis to efficiently handle user profile data. Using Apache Thrift allows for robust, cross-language services, while Redis serves as a high-performance cache to enhance data retrieval speeds.

## Technologies

### Apache Thrift

Apache Thrift is a software framework developed by Facebook for scalable cross-language services development. It combines a software stack with a code generation engine to build efficient services that can work seamlessly across multiple programming languages.

- Thrift supports programming languages; C++, Java, Python, PHP, Ruby, Erlang, Perl, Haskell, C#, Cocoa, JavaScript, Node.js, Smalltalk, and others.

- Thrift uses an IDL to define data types and service interfaces, which are then used to generate source code in various languages.

- Includes a complete stack for building clients and servers with transport and protocol abstraction, allowing easy switch between binary, JSON, HTTP, non-blocking servers, and more.

- By enabling efficient communication across services written in different languages, Thrift is useful in heterogeneous environments where different systems need to interact seamlessly.

- Thrift's built-in functionalities are designed for scalability, making it suitable for large-scale distributed system deployments.

- One disadvantage of using Thrift is its rigidity. Changes to the IDL require recompiling and redeploying dependent services, which can introduce delays and complexity in continuous deployment environments.

### Docker

Docker is an open-source platform for developing, shipping, and running applications. Docker enables you to seperate your applications from your infrastructure so you can deliver software quickly.

- Docker packages software into standardized units called containers that have everything the software needs to run including libraries, system tools, code, and runtime

- Containers are isolated from each other and enable you to run multiple applications on the same host.

- Once a Docker container is created, it can be run on any machine that has Docker installed, regardless of the operating environment.

- Docker makes it easy to scale out applications and microservices by adding new containers for new modules and functionalities.

- Containers share the host OS kernel, so if a container is compromised, it could potentially compromise all other containers on the same host.

## Project Structure

- `server.ipynb`: Contains the Thrift server implementation.

- `client.ipynb`: Contains the Thrift client implementation.

- `Dockerfile`: Configures the Docker environment for both server and client.

- `docker-compose.yml`: Manages the Docker services for the project.

- `SimpleService.thrift`: Contains IDL that defines services

- `gen_py`: Containing all the necessary Python files to implement the service.

## Project Setup

### Thrift IDL

#### SimpleService.thrift

- Namespaces in Thrift are similar to namespaces or packages in other programming languages; they prevent naming conflicts and organize code.

- Thrift supports a variety of data types, including basic types (int, string, bool), structured types (structs), and containers (lists, sets, maps). 

- Thrift defines a set of methods that can be called remotely

- Run `thrift --gen py SimpleService.thrift` to generate the python code.

### Docker implementation

The Docker environment is made to ensure smooth deployment and operation of the services. Here’s a detailed overview of the Docker-related files and configurations:

#### Dockerfile

The Dockerfile sets up the environment necessary to run both the server and client components of the Thrift application.

- Uses `python:3.8-slim` as a lightweight base image, which is ideal for Python applications that require a minimal resource.

- Installs all necessary Python dependencies, ensuring that both the Thrift framework and Jupyter notebook libraries are available.

- Exposes port 8888, which is standard for Jupyter Notebooks, facilitating easy access to the application interface.

#### Docker-compose.yaml

Manages the Thrift server and client, ensuring that all components can interact seamlessly.

- **Configuration**:

  - Defines two services: `thrift-server` and `thrift-client`

  - The build context is set to the current directory (.), meaning Docker will look for the Dockerfile in the project's root.

  - Specifies which Dockerfile to use for building the image. It is located in the root directory as indicated by the context.

  - Exposes port 8888 for the server, typically used for accessing web interfaces like Jupyter Notebooks.

  - Additionally exposes port 9090, which is used for the Thrift server to communicate with client.

  - Maps port 8889 on the host to port 8888 inside the container for the client, allowing access to the client's Jupyter Notebook running on the default port 8888

- Building the Docker Image:
 - Use Dockerfile to build the Docker image by executing `docker build -t <your_image_name> .`
 - Replace `<your_image_name>` to name your docker image.

- Running the Docker Containers:

 - Start the Docker containers with `docker-compose up`.

 - Docker Compose will create and launch containers for the redis and notebook services.

 - Access the Jupyter Notebook server to run server side at `http://localhost:8888` in a web browser.
 
 - Access the Jupyter Notebook server to run client side at `http://localhost:8889` in a web browser.

- To stop containers, press `Ctrl + C` in the terminal running `docker-compose up`.

## Python Script Overview

### server.ipynb

#### Methods

- `sayHello(name)`: Returns a greeting string, demonstrating a simple string return type.

- `addNumbers(num1, num2)`: Returns the sum of two numbers, showcasing basic arithmetic operation.

- `getPersonInfo(personId)`: Returns a Person struct, illustrating how complex data types are handled.

- `istStudents(department)`: Returns a list of Student structs, showing list handling capabilities.

- `countVotes(votes)`: Accepts and returns a dictionary to demonstrate map functionality.

- `findPersonByEmail(email)`: Includes error handling by raising a custom PersonNotFound exception if the email does not match, demonstrating Thrift's exception handling capabilities.

- `logMessage(message)`: A one-way method that logs a message to the server console, exemplifying non-blocking calls.

- The server uses `TServerSocket` for network communications, `TBufferedTransport` for efficient data transmission, and `TBinaryProtocol` for binary serialization of data.

### client.ipynb

- Establishes a connection to the server using `TSocket` connected to the server's hostname (`thrift-server`) and port `9090`.

- Utilizes `TBufferedTransport` and `TBinaryProtocol` similar to the server for compatibility in data handling and serialization.

- RPC Calls:
  - Makes remote calls to the server for each method defined in the server's interface, handling normal responses and exceptions.
  - Displays how client-side interaction with Thrift services works, and how data types and exceptions are managed across the network.

- Demonstrates robust error handling by catching and printing errors related to network issues or Thrift operations, including custom exceptions like PersonNotFound.

#### Instructions

- After running Docker server is online, navigate to `http://localhost:8888` and `http://localhost:8889` in a web browser.

- Open server.ipynb in `http://localhost:8888` and client.ipynb in `http://localhost:8889`.

- Run the server.ipynb first, then client.ipynb.

- The output should look like:
```
Hello, Alvino!
1 + 2 = 3
Person Info: Person(id=1, name='Alvino Angelo', age=23, email='alvino@umd.edu')
List Students: [Student(id=1, name='Alvino', department='Engineering'), Student(id=2, name='Bob', department='Engineering')]
Vote Count: {'Alvino': 3, 'Bob': 5}
Find Person by Email: Person(id=1, name='Alvino Angelo', age=23, email='alvino@umd.edu')
No person found with email alvinoangelo@umd.edu
```

## Conclusion

The server-client setup in this project exemplifies the use of Apache Thrift for RPCs in a microservices architecture. It highlights how different data types, error handling, and one-way operations can be effectively implemented and managed within a distributed system. Both server and client in Jupyter Notebooks helps in understanding the flow of data and the behavior of Thrift services in real-time. Apache Thrift's cross-language compatibility and scalable architecture are important for developing services that need  interactions between different programming languages, facilitating a more inclusive and versatile development environment. Possible future developments include enhancing security, integrating microservices for more complex data interactions, and exploring advanced features of Apache Thrift to handle real-time data processing and complex querying.