# Use a base image with Python and Java installed
FROM  ubuntu:20.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Update and install necessary packages
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends apt-utils && \
    apt-get install -y openjdk-8-jdk python3.10 python3-pip wget && \
    rm -rf /var/lib/apt/lists/*

# Attempt to find the correct JAVA_HOME
RUN echo "Checking Java directories..." && \
    find /usr/lib/jvm/ -name 'java-*-openjdk*' -type d

RUN update-alternatives --list java

# Find the correct JAVA_HOME and set it
ENV JAVA_HOME /usr/lib/jvm/java-8-openjdk-arm64/
ENV PATH=$PATH:$JAVA_HOME/bin
RUN export JAVA_HOME

# Display Java include directory
RUN echo "JAVA_HOME is set to ${JAVA_HOME}"


# Install Flink
RUN python3 -m pip install apache-flink

# Set the working directory
WORKDIR /app


# Copy the Python script 
COPY app.py .
COPY . .


# Expose the necessary port (e.g., for Flink web UI)
EXPOSE 8081

# Default command to run when starting the container
CMD ["python3", "app.py"]

