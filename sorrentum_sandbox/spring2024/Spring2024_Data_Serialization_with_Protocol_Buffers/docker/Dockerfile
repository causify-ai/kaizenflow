# Use the Python 3.8 slim-buster base image
FROM python:3.8-slim-buster

# Set the working directory to /app
WORKDIR /app

# Copy python package requirements file into /app
COPY requirements.txt requirements.txt

# Install Protocol Buffers Compiler
RUN apt-get update && apt-get install -y protobuf-compiler

# Install Python Protocol Buffers Library
RUN pip3 install -r requirements.txt

# Copy the entire application code to the working directory
COPY . .

# Compile the student.proto file into the student_pb2.py file
RUN protoc --python_out=. student.proto
