# Use an official Python runtime as a parent image.
FROM python:3.11.7

# Set the working directory in the container.
WORKDIR /app

# Copy the current directory contents into the container at /usr/src/app.
COPY . .

# Install any needed packages specified in requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8082 available to the world outside this container.
EXPOSE 8082

# Define environment variable.
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0

# Run app.py when the container launches.
CMD ["python", "app.py"]