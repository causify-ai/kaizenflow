# Using jupyter/pyspark-notebook ubuntu-22.04 as base image
FROM jupyter/pyspark-notebook:x86_64-ubuntu-22.04

# Set the working directory in the container to /app
WORKDIR /app

# Install Pyspark to fulfill dependencies of the project
RUN pip install --no-input --no-cache-dir pyspark==3.5.1

# Copy the current directory contents into the container at /app
COPY * .

# Expose the port the notebook runs on
EXPOSE 8888

# Run Jupyter Notebook when the container launches
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root", "--NotebookApp.token=''"]
