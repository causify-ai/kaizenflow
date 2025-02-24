FROM python:3.9

# Set the working directory in the container.
WORKDIR /app

# Copy the current directory contents into the container at /app.
COPY . .

# Install necessary packages.
RUN pip install --no-cache-dir \
    pymongo \
    redis \
    ratelimit \
    scikit-learn \
    pandas \
    matplotlib

RUN pip install jupyter

# Expose the port Jupyter Notebook runs on.
EXPOSE 8888

# Change ownership of the MongoDB data directory.
RUN mkdir -p /docker/mongodb_data/diagnostic.data && \
    chown -R 999:999 /docker/mongodb_data

# Run Jupyter Notebook when the container launches.
CMD ["jupyter", "notebook", "--ip=0.0.0.0", "--port=8888", "--no-browser", "--allow-root"]
