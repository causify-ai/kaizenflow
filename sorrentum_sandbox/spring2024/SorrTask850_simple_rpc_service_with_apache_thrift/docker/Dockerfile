# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Install Jupyter
RUN pip install notebook thrift

# Set the working directory
WORKDIR /app

# Copy the notebooks into the container
COPY . /app

# Expose the notebook port
EXPOSE 8888

# Run Jupyter Notebook
CMD ["jupyter", "notebook", "--ip='0.0.0.0'", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]
