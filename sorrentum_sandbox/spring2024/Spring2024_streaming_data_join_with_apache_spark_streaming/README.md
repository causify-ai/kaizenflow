
## Project Title: Spark Streaming Join Operations
Author: Ayushi Prasad
GitHUb account: AYUSHIPRASAD
UMD email: aprasad5@umd.edu

### Description:
This project demonstrates how to perform join operations using Spark Streaming, a component of Apache Spark, which enables scalable, high-throughput, fault-tolerant stream processing of live data streams.


Link to video: [Youtube](https://youtu.be/uZ9u6eFLtZo)


## Running Instructions

1. Building the Docker Image: ```docker build -t ayushi_data605:v1.0 . ```

2. Running the Docker Container: ```docker run --rm -it -p 8888:8888 ayushi_data605:v1.0```

3. Accessing the Jupyter Notebook Server: Navigate to ```http://localhost:8888``` in a web browser to access the Jupyter Notebook interface

4. Stopping the Docker Containers: To stop containers, press ```Ctrl + C``` in the terminal
## Requirements

* Python 3.x
* Apache Spark (installation instructions can be found at https://spark.apache.org/downloads.html)
* PySpark (Python API for Spark, can be installed via pip: pip install pyspark)

## Technologies

### Apache Spark Streaming: Real-Time Stream Processing

* Apache Spark Streaming is a powerful real-time stream processing framework designed for high-throughput, fault-tolerant stream processing of live data streams.

* Functioning as a micro-batch processing engine, Spark Streaming divides continuous streams of data into small, manageable batches, enabling parallel and scalable processing.

* It provides a rich set of high-level APIs, with DStream (Discretized Stream) being one of its core abstractions. DStreams represent a continuous stream of data divided into small batches, similar to RDDs (Resilient Distributed Datasets) in batch processing.

* Apache Spark Streaming supports various data sources, including Kafka, Flume, and TCP sockets, making it adaptable to diverse streaming data scenarios.

* Spark Streaming is often utilized for real-time analytics, monitoring, and ETL (Extract, Transform, Load) operations, enabling organizations to derive insights and take action on data as it arrives.

* The DStream API serves as the backbone of this project, enabling developers to process and analyze streaming data in real-time.

* The function that aggregates user interactions exemplifies the versatility of Spark Streaming's DStream API.

* It consumes a continuous stream of user interaction events, such as clicks or views, from a data source.

* Using DStream transformations and actions, it computes aggregate metrics, such as the total number of interactions per user or the most popular pages.

* These computations are performed in real-time on small batches of data, ensuring low latency and enabling near real-time insights.

* The fault-tolerant nature of Spark Streaming ensures that in the event of failures, data is reliably processed and results are accurately computed, providing robustness to the streaming application.

* By leveraging Spark Streaming's DStream API, developers can build scalable, responsive, and fault-tolerant stream processing applications that meet the demands of modern real-time data processing needs.

### Docker: Simplifying Application Management

* Docker offers a streamlined way to handle applications, from development to deployment. It allows developers to bundle an app and its necessary components into small, portable containers.

* These containers run consistently across different systems, ensuring that the application behaves the same in testing, development, and production environments.

* Using Docker, developers write a Dockerfile—a simple recipe that tells Docker how to build the app's container. For instance, it may instruct Docker to use a Python base image, install Redis, and copy the project files.

* Once the Docker image is built, it can be easily deployed anywhere Docker is installed. This enables the application to run on any system without concerns about setup or compatibility issues.

* Docker simplifies the process of managing dependencies, deploying applications, and collaborating with teammates. It represents a significant advancement in modern software development, facilitating the building, shipping, and running of applications in any environment.




## Usage

1. Run the Python file using the command python spark_streaming_join.py.
2. The program will initialize a SparkContext and create a StreamingContext with a batch interval of 10 seconds.
3. It generates sample data and creates DStreams (discretized streams) from queues of RDDs (Resilient Distributed Datasets).
4. Two different window operations (10-second and 20-second windows) are applied to the DStreams, followed by counting occurrences of each element.
5. Inner join and left outer join operations are performed between the two datasets.
6. The program prints the results of each operation periodically as the streaming data is processed.
7. The program will terminate automatically after 30 seconds.
## Input Schema

### Mock input schema for dataset1 and dataset2
```
# Dataset 1
dataset1_schema = {
    "timestamp": "2024-05-10 18:11:30",  # Timestamp indicating when the data was collected
    "data": [
        {"value": 0},
        {"value": 2},
        {"value": 4},
        {"value": 6},
        {"value": 8},
        {"value": 1},
        {"value": 3},
        {"value": 5},
        {"value": 7},
        {"value": 9}
    ]
}

# Dataset 2
dataset2_schema = {
    "timestamp": "2024-05-10 18:11:30",  # Timestamp indicating when the data was collected
    "data": [
        {"value": 0},
        {"value": 2},
        {"value": 4},
        {"value": 1},
        {"value": 3}
    ]
}
```
```
# Explanation:
- Each dataset consists of a timestamp indicating when the data was collected and a list of data elements.
- Each data element contains a "value" representing the element value.
- The timestamp is the same for both datasets since they are collected simultaneously.
- The values in each dataset correspond to the elements generated in the Spark Streaming code,where each element is mapped to its remainder when divided by a certain number.
- Dataset 1 has a 10-second window while Dataset 2 has a 20-second window.
- Both datasets are then reduced by key to count the occurrences within the specified window.
```

## Understanding the Code

1. 
```
# Initialize an empty list to hold RDDs
rdd_queue = []

# Create 5 batches of data
for i in range(5):
    # Generate data ranging from 0 to 999
    rdd_data = range(1000)

    # Create an RDD from the generated data
    rdd = ssc.sparkContext.parallelize(rdd_data)

    # Append the RDD to the list
    rdd_queue.append(rdd)

# Print the list of RDDs
pprint(rdd_queue)
```

The code sets up a simulated stream of data by creating 5 RDDs, each containing numbers from 0 to 999. These RDDs are then added to the rdd_queue list, which will be used to create a DStream in the Spark Streaming context.

RDD Creation and Addition to Queue:

``` rdd = ssc.sparkContext.parallelize(rdd_data)```: Parallelizes the generated rdd_data range into an RDD using the SparkContext. Each RDD contains the numbers from 0 to 999.

``` rdd_queue.append(rdd)```: Appends the created RDD (rdd) to the rdd_queue list. Each RDD in this list represents a batch of data in the stream.

2. 
``` 
# Create a DStream from a queue of RDDs, mapping each element to (remainder, 1), apply a 10-second window, and count occurrences.
dataset1 = ssc.queueStream(rdd_queue).map(lambda x: (x % 10, 1)).window(10).reduceByKey(lambda v1, v2: v1 + v2)
# Print the result of dataset1 DStream
dataset1.pprint() 
```

```ssc.queueStream(rdd_queue)```: Creates a DStream from rdd_queue.

```.map(lambda x: (x % 10, 1))```: Applies a transformation to each element of the DStream, mapping it to a tuple (x % 10, 1). This groups elements by their remainder when divided by 10, converting each element into a key-value pair with the key as the remainder and the value as 1.

```.window(10)```: Creates a sliding window of 10 seconds on the DStream, collecting elements over this time frame.

```.reduceByKey(lambda v1, v2: v1 + v2```: Reduces elements with the same key by adding their values together. In this case, it counts the occurrences of each remainder within the 10-second window.

3. 
```
# Create a DStream from a queue of RDDs, mapping each element to (remainder, 1), apply a 20-second window, and count occurrences.
dataset2 = ssc.queueStream(rdd_queue).map(lambda x: (x % 5, 1)).window(windowDuration=20).reduceByKey(lambda v1, v2: v1 + v2)
# Print the result of dataset2 DStream
dataset2.pprint()

```

The code above constructs a streaming computation pipeline similar to the previous one but with a 20 seconds window duration and grouping based on the remainder when dividing by 5.

4. 
The code performs an inner join operation between two DStreams.

In both cases, the key is computed as the remainder when dividing each element x by either 10 (for dataset1) or 5 (for dataset2). Therefore, the common key between the two datasets is the remainder of dividing each element by 5.

```
# Perform an inner join operation between dataset1 and dataset2
joinedStream = dataset1.join(dataset2)

# Print the output of the joinedStream
joinedStream.pprint()

```
```
# Perform left outer join operation between dataset1 and dataset2
joinedStream_left_outer = dataset1.leftOuterJoin(dataset2)

# Print the output of the joinedStream
joinedStream_left_outer.pprint()
```
## Understanding the Output

### Inner Join:

The joined counts from ```dataset1``` and ```dataset2``` represent the combined results of the inner join operation performed between the two datasets. In the provided output, the joined counts are displayed as tuples where the first element corresponds to the key (remainder) and the second element is a tuple containing the count from ```dataset1``` and ```dataset2``` respectively.

At the timestamp ```"Time: 2024-05-10 18:11:30"```, the joined count for key 0 is (100, 200). This means that within the specified window duration:

* Key 0 appears 100 times in ```dataset1```.

* Key 0 appears 200 times in ```dataset2```.

### Left Outer Join:

A left outer join operation between two DStreams combines elements from the left DStream with matching elements from the right DStream, based on a common key. Left outer join returns all records from the left dataset (```dataset1```) and matching records from the right dataset (```dataset2```), if any. If a key exists in dataset1 but not in ```dataset2```, the corresponding value in the second element of the tuple is None.

At the timestamp ```"Time: 2024-05-10 18:11:30"```, the joined count for key 6 is (100, None). This means that within the specified window duration:

* Key 6 appears 100 times in ```dataset1```.

* Key 6 doesnot appear in ```dataset2```.


### Comparison:

1. Inner join focuses on the intersection of keys present in both datasets, filtering out non-matching keys.

2. Left outer join retains all keys from the left dataset (```dataset1```), including those that do not have a match in the right dataset (```dataset2```), represented by None in the output.
## Notes

* This project serves as a basic demonstration of Spark Streaming join operations and can be extended for more complex use cases.
* Adjustments to batch intervals, window durations, and data generation can be made according to specific requirements.
## How different Joins Work

### How Inner Join works:
![Inner Join](https://miro.medium.com/v2/resize:fit:640/format:webp/1*PznjPX_BMOo8D8Xty3dC6w.png)

### How Left Outer Join works:
![Left Outer Join](https://miro.medium.com/v2/resize:fit:640/format:webp/1*_R6_wM30ki89sOt7ZYOXOQ.png)