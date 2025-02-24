# DS605 Final Project

In this project I mainly used Pyspark, Python and Docker.

PySpark is a Python library for Apache Spark that provides all the core functionality of Spark, including RDD (Resilient Distributed Dataset), DataFrame, SQL, MLlib (Machine Learning Library), and GraphX (Graph Computation Library). PySpark allows us to run Spark tasks directly using Python's API, which is much more efficient than using python directly for data processing. Also Pyspark provides functions like SQL queries, streaming calculations, machine learning, etc. In this way, we can directly call the SQL script directly through PySpark by starting it with the spark-sql command.

## Pros:

Pyspark runs fast. It uses a DAG scheduler, query optimizer, and physical execution engine to achieve high performance on batch and streaming data.

Pyspark is easy to use. It supports Java, Scala, Python, R, and SQL, and offers more than 80 operators that make it easy to build parallel applications.

Pyspark has universality. It combines SQL, stream processing, and complex analytics, and offers a wide range of libraries, including SQL and DataFrames, MLlib for machine learning, GraphX, and Spark Streams, which makes it easy to combine these libraries in one application.

## Cons:

In a big data scenario, if there are frequent data communication operations in the code, this way the JVM and Python processes will interact frequently, which may lead to a crash.

## Citation:

[Pyspark document](https://spark.apache.org/docs/3.3.1/api/python/index.html)

[Pyspark tutorial](https://www.datacamp.com/tutorial/pyspark-tutorial-getting-started-with-pyspark)

## Logic of Docker System

In dockerfile, I used python:3.11.8-slim as base image. Then set the working directory in the container to /app, and copy the current directory contents into that. This project requires several python libraries and java jdk support, so in the next step I downloaded these supports. Finally I exposed the port and run the python script when the container launches.

After creating the image, A running instance can be created from the docker image, i.e., the docker container. I used docker desktop to monitor image and container usage. From the application, the base docker image hierarchy is debian:12-slim and python:3.11-slim. And there are 23 layers in the image I created.

## Run the system

First build the image in the dockerfile directory:

`docker build -t mllib .`

it will return:

`[+] Building 89.2s (13/13) FINISHED                                                                                                               docker:default => [internal] load build definition from Dockerfile                                                                                                        0.0s => => transferring dockerfile: 300B                                                                                                                        0.0s => [internal] load metadata for docker.io/library/python:3.11.8-slim                                                                                       0.8s => [auth] library/python:pull token for registry-1.docker.io                                                                                             0.0s View a summary of image vulnerabilities and recommendations → docker scout quickview`

Then run the container:

`docker run mllib`

It will return the result from the python script and some warnings because of the java environment:

`2024-05-10 22:51:09 Setting default log level to "WARN". 2024-05-10 22:51:09 To adjust logging level use sc.setLogLevel(newLevel). For SparkR, use setLogLevel(newLevel). 2024-05-10 22:51:09 24/05/11 02:51:09 WARN NativeCodeLoader: Unable to load native-hadoop library for your platform... using builtin-java classes where applicable 24/05/11 02:51:15 WARN InstanceBuilder: Failed to load implementation from:dev.ludovic.netlib.blas.JNIBLAS 2024-05-10 22:51:15 24/05/11 02:51:15 WARN InstanceBuilder: Failed to load implementation from:dev.ludovic.netlib.blas.VectorBLAS 2024-05-10 22:51:19 24/05/11 02:51:19 WARN SparkStringUtils: Truncated the string representation of a plan since it was too large. This behavior can be adjusted by setting 'spark.sql.debug.maxToStringFields'.`
