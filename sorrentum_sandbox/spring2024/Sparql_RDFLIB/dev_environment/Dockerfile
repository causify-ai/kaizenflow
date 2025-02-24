# Use an official Python runtime as a parent image
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install dependencies
RUN apt-get update && \
    apt-get install -y libxml2-dev libxslt-dev lib32z1-dev && \
    apt-get clean

# Install Jupyter
RUN pip install --no-cache-dir jupyter

# Install RDFLIB and any other Python dependencies
RUN pip install --no-cache-dir rdflib

# Set an environment variable for SPARQL endpoint URL
ENV SPARQL_ENDPOINT_URL="http://example.com/sparql"

# Copy the rest of your application code into the container
COPY . .

# Expose the Jupyter port
EXPOSE 8888

# Command to run Jupyter Notebook
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
