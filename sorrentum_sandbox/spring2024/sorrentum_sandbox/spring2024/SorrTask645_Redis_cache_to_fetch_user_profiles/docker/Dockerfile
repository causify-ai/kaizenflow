# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container to /app
WORKDIR /app


# Install Jupyter Notebook and Redis client
RUN pip install --no-cache-dir redis notebook

# Copy the current directory contents into the container at /app
COPY . .

# Expose the port the notebook runs on
EXPOSE 8888

# Run Jupyter Notebook when the container launches
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]
