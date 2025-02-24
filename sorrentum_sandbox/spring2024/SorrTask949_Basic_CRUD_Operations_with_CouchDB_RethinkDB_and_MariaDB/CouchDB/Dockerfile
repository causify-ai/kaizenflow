# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Install Python and Pip
RUN apt-get update && apt-get install -y python3 python3-pip

# Install virtual environment
RUN pip install virtualenv

# Install Python and Pip
RUN apt-get update && apt-get install -y python3 python3-pip

# Install virtual environment
RUN pip install virtualenv

# Create a virtual environment in the container
RUN python -m venv /app/venv


# Install curl
RUN apt-get update && apt-get install -y curl

# Set the working directory in the container
WORKDIR /app

# Copy just the requirements.txt initially to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

# Install any needed packages specified in requirements.txt
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . /app



# Make port 5000 available to the world outside this container
EXPOSE 5000

# Define environment variable
ENV NAME World

# Run the Python application
CMD ["python", "app.py"]
