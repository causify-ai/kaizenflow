# CRUD Operations with CouchDB, RethinkDB, and MariaDB

## Author info

- Author: Rutvik Patel
- GitHub account: rutvik5rv
- UMD email: rvpatel@umd.edu
- Personal email: rutvik5rv@gmail.com

## Description

This project demonstrates basic CRUD (Create, Read, Update, Delete) operations across three different database systems: CouchDB, RethinkDB, and MariaDB. 
Each system offers unique features and capabilities for data management. The Python project utilizes specific libraries for each database to perform CRUD operations, showcasing basic data manipulation techniques across these platforms.
Video link: https://drive.google.com/drive/folders/1A18z9Qyvb_jrg5AGj29YuZ3EkiVn_RzD?usp=drive_link



## Technologies

- **CouchDB**: An open-source NoSQL database that uses JSON for documents, JavaScript for MapReduce indexes, and regular HTTP for its API.
- **RethinkDB**: A JSON-based NoSQL database that automatically syncs data in realtime between users and servers.
- **MariaDB**: A community-developed, commercially supported fork of the MySQL relational database management system.
- **Python libraries**:
  - `python-couchdb` for interacting with CouchDB.
  - `rethinkdb` for managing RethinkDB operations.
  - `mysql-connector-python` for connecting to MariaDB.
- **Flask**: A micro web framework written in Python, used for handling web requests.
- **Docker**: Simplifies deployment by containerizing the application and its dependencies.

# Project Components Explanation

## CouchDB

**CouchDB** is an open-source NoSQL database that focuses on ease of use. It is based on JSON to store data, uses JavaScript as its query language, and WebHTTP for an API. CouchDB is designed to work well with modern web and mobile apps.

### Files related to CouchDB in the project:
- `app.py`: Contains the Flask routes that handle CRUD operations specifically tailored for CouchDB using the `python-couchdb` library. The CRUD functions interact with CouchDB to create, read, update, and delete documents.
- `Dockerfile`: Includes commands to set up the Python environment where `python-couchdb` is installed to interact with CouchDB.
- `docker-compose.yml`: Defines a CouchDB service that runs the official CouchDB Docker image, exposing the default port and setting up initial configurations like admin user and password.

## RethinkDB

**RethinkDB** is a JSON-based, open-source NoSQL database that facilitates real-time web applications. It pushes updates to the application in real-time instead of polling the database for changes. It’s well-suited for applications that require real-time feeds to their data.

### Files related to RethinkDB in the project:
- `app.py`: Incorporates routes for performing CRUD operations on RethinkDB. These operations use the `rethinkdb` Python library to connect to the database and manipulate the data.
- `Dockerfile`: Ensures the Python environment is prepared to include the `rethinkdb` library.
- `docker-compose.yml`: Configures the RethinkDB service using its official Docker image, specifies ports, and manages database initialization settings.

## MariaDB

**MariaDB** is a community-developed fork of MySQL and is one of the most popular database servers in the world. Being a relational database, it uses SQL (Structured Query Language) to access and manage the data, which is organized into tables.

### Files related to MariaDB in the project:
- `app.py`: Defines Flask routes that facilitate CRUD operations on MariaDB using `mysql-connector-python` for connecting and executing SQL statements.
- `Dockerfile`: Lists commands for installing `mysql-connector-python` within the Python environment.
- `docker-compose.yml`: Outlines the MariaDB service setup with the necessary environment variables like root password, and exposes the default SQL port for connections.

# Explaining Docker, Flask, and GitHub Usage

## Docker

### What is Docker?
Docker is a set of platform as a service (PaaS) products that use OS-level virtualization to deliver software in packages called containers. Containers are isolated from one another and bundle their own software, libraries, and configuration files; they can communicate with each other through well-defined channels.

### Why Use Docker?
- **Consistency Across Environments**: Docker ensures that the application runs the same way in different environments, be it development, testing, or production. This consistency eliminates the "it works on my machine" problem.
- **Simplicity and Speed**: Docker containers can be configured once and run anywhere, simplifying setup. They also make use of snapshots and image layers, which speeds up the development and deployment processes.
- **Isolation**: Each service (CouchDB, RethinkDB, MariaDB, Flask app) runs in its own container, ensuring they do not interfere with each other. This isolation helps in easy management and scaling of services.

### Docker in the Project
In this project, Docker is used to manage and run the Flask application along with the three different databases—CouchDB, RethinkDB, and MariaDB—each in separate containers. The configurations are defined in the `docker-compose.yml` file, which simplifies the management of these multi-container setups.

## Flask

### What is Flask?
Flask is a micro web application framework written in Python. It is classified as a microframework because it does not require particular tools or libraries but supports extensions that can add application features as if they were implemented in Flask itself.

### Why Use Flask?
- **Simplicity and Flexibility**: Flask's simple and easy-to-understand syntax makes it perfect for small projects as well as large scale applications. Its flexibility allows developers to use the right tools for their tasks.
- **Lightweight**: Flask has minimal core dependencies, making it lightweight and easy to add only the tools needed, which keeps the application efficient.
- **Rapid Development**: Flask allows for fast development of web applications, thanks to its ability to reload code changes on the fly and its helpful debugging tools.

### Flask in the Project
Flask is used as the backend framework for handling HTTP requests and responding with data from the databases. It is responsible for handling the CRUD operations that interact with the databases and serving the results to the user.

## GitHub

### What is GitHub?
GitHub is a code hosting platform for version control and collaboration. It lets you and others work together on projects from anywhere. It is built on Git, a distributed version control system.

### Why Use GitHub?
- **Version Control**: GitHub uses Git to manage different versions of project files. It allows tracking changes, reverting to previous stages, and efficient handling of project updates.
- **Collaboration**: Multiple people can work together on a project from any location. GitHub provides tools such as issues, pull requests, and project boards that facilitate seamless collaboration among team members.
- **Documentation and Management**: GitHub supports additional documentation for projects, such as wikis. It also provides a comprehensive way to manage projects through milestones, labels, and assignees.

### GitHub in the Project
GitHub hosts the repository containing all project files, ensuring that changes are tracked and that team members can collaborate efficiently. It serves as the central hub for source code management, issue tracking, and feature requests, helping maintain the project's lifecycle.

 # Docker System for CRUD Operations with CouchDB, RethinkDB, and MariaDB

## Overview

This Docker system is designed to facilitate a development environment that supports CRUD (Create, Read, Update, Delete) operations on three different databases: CouchDB, RethinkDB, and MariaDB. Each database has its own dedicated Docker container to ensure that they are isolated from one another, which helps in maintaining the integrity and independence of each database's data and operations.

## Docker Architecture

The architecture consists of three main parts, each configured to run within its own Docker container:

1. **CouchDB** - An open-source NoSQL database, known for its easy scalability and flexible data structure.
2. **RethinkDB** - A NoSQL database optimized for real-time web applications.
3. **MariaDB** - A relational database that is a fork of MySQL, known for its performance and reliability.

Each part of the application (CouchDB, RethinkDB, and MariaDB) has been containerized using Docker to provide a consistent and isolated environment for development and testing.

## Docker Configuration

### Dockerfile

Each Dockerfile in the project setups up the necessary environment for the Python Flask application that interacts with one of the databases. It includes:

- Pulling the base image (usually Python 3.8-slim).
- Installing Python packages that are required for connecting and operating the database using a `requirements.txt` file.
- Copying the application source code into the container.

### docker-compose.yml

The `docker-compose.yml` file for each database defines how the containers should be built and run. It specifies:

- The services required (the database and the Flask app).
- The Docker images to use for the databases.
- Port mappings that expose the databases and the Flask app on specified ports.
- Environment variables necessary for the databases (such as user credentials and database names).
- Volumes for persistent data storage outside of the containers.

## Running the System

To run the Docker system for each database, you will need to perform the following steps:

1. **Navigate to the Directory**:
   Go to the directory specific to the database you want to operate. Each directory contains a `run_docker.sh` script tailored for its respective database.

2. **Run the Docker Script**:
   Execute the `run_docker.sh` script to build and start the Docker containers. This can be done using the following command:
   ```bash
   ./run_docker.sh


# Overview of Python Scripts for CRUD Operations

It provides a detailed overview of the Python scripts designed for handling CRUD (Create, Read, Update, Delete) operations for CouchDB, RethinkDB, and MariaDB. Each script is tailored to interact with its respective database using Flask, a lightweight WSGI web application framework in Python.

## CouchDB: `app.py`

### Functionality:
- **Create**: Inserts new documents into the CouchDB database. Each document's structure is defined within the script, typically including fields like name, age, and other relevant data.
- **Read**: Fetches documents from CouchDB. It can retrieve a single document by ID or all documents within a specific collection.
- **Update**: Modifies existing documents in CouchDB. The script identifies documents by ID and applies updates to fields such as name, age, or other attributes.
- **Delete**: Removes documents from CouchDB based on their ID.

### Role:
The script serves as the backend component of a Flask application. It handles HTTP requests that perform CRUD operations on the CouchDB database. Each operation is accessible via specific routes (endpoints) defined in the Flask app.

## RethinkDB: `app.py`

### Functionality:
- **Create**: Adds new entries to tables in RethinkDB. The data schema for entries typically includes fields relevant to the application's context, like user data or transaction details.
- **Read**: Retrieves data from RethinkDB. This includes reading specific entries using unique identifiers or querying multiple entries based on certain conditions.
- **Update**: Updates existing entries in RethinkDB. This script can change specific fields of entries, reflecting new data or corrections.
- **Delete**: Deletes entries from a table in RethinkDB based on a specified criterion, typically an ID.

### Role:
This script also acts as a backend for a Flask application, handling requests to interact with the RethinkDB database. It defines routes that the frontend can call to perform database operations, effectively communicating with the database and returning results to the user.

## MariaDB: `app.py`

### Functionality:
- **Create**: Executes SQL commands to insert new records into MariaDB tables. The records adhere to the relational schema defined in the database.
- **Read**: Performs SQL queries to fetch records from MariaDB. It can be configured to fetch all records or filter records based on specific fields.
- **Update**: Runs SQL update statements to modify existing records in MariaDB tables. Updates can involve one or more fields, depending on the operation's requirements.
- **Delete**: Deletes records from MariaDB using SQL delete commands, typically targeting records based on their unique identifiers.

### Role:
As with the other scripts, this serves as the backend for a Flask application specifically designed for MariaDB operations. It defines various endpoints for CRUD operations, processing HTTP requests, executing the corresponding SQL commands in MariaDB, and returning the outcomes to the client.


# Conclusion

The "CRUD Operations with CouchDB, RethinkDB, and MariaDB" project exemplifies a robust implementation of basic database operations across three distinct database systems using a unified Python-Flask application framework. Each part of the project—CouchDB, RethinkDB, and MariaDB—brings unique features and capabilities to the table, from CouchDB's flexible JSON-based document structure to MariaDB's efficient relational data handling and RethinkDB's real-time data synchronization.

## Key Takeaways

- **Technology Integration**: By integrating Flask, Docker, and GitHub, the project achieves a seamless development workflow that is easy to set up, test, and scale. Flask's lightweight and flexible nature allows for straightforward routing and request handling, which is essential for CRUD operations. Docker enhances the deployment process, ensuring that each database environment is isolated and consistent, thus preventing "it works on my machine" issues. GitHub provides a platform for version control and collaboration, enabling ongoing development and iteration of the project.
  
- **Real-World Application**: The project serves as an excellent reference for developers looking to understand or implement CRUD operations across different databases. The distinct characteristics of each database system are harnessed to demonstrate specific data management techniques, making the project not only a learning tool but also a practical blueprint for real-world applications.

- **Scalability and Maintenance**: The use of Docker containers ensures that the application components can be easily scaled and maintained. The containerization of each database and the Flask app allows developers to update, modify, or scale parts of the application independently without affecting the entire system.

## Future Directions

Moving forward, the project can be expanded in several ways:
- **API Development**: Enhance the Flask application to provide a more comprehensive RESTful API interface, allowing for better interaction with other applications and services.
- **Front-end Integration**: Develop a front-end interface to provide users with a graphical user interface (GUI) for performing CRUD operations, improving the user experience and accessibility.
- **Performance Optimization**: Conduct performance benchmarks to optimize CRUD operations, especially in scenarios involving large datasets and complex queries.

In conclusion, this project not only demonstrates the capability to manage different database systems effectively but also sets a foundation for more complex applications that require real-time data handling, reliable data storage, and efficient data retrieval. It stands as a testament to the power of integrating modern development tools and technologies to build scalable and robust applications.
