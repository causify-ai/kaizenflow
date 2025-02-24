# Start with an OpenJDK image which includes Java
FROM openjdk:11-slim

# Install Python.
RUN apt-get update && apt-get install -y python3-pip python3-dev && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Copy application files
COPY 605_Final_Project.py /app/
COPY requirements.txt /app/

# Install Python dependencies
RUN pip3 install --no-cache-dir -r requirements.txt

# Set environment variables to configure PySpark to use Python 3
ENV PYSPARK_PYTHON=python3

# Add GraphFrames and other dependencies on the fly when initializing PySpark
ENV PYSPARK_SUBMIT_ARGS="--packages graphframes:graphframes:0.8.2-spark3.2-s_2.12 pyspark-shell"

# Run the Python script using spark-submit when the container launches
CMD ["spark-submit", "--packages", "graphframes:graphframes:0.8.2-spark3.2-s_2.12", "605_Final_Project.py"]