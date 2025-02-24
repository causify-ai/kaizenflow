# Use an official Python runtime as a parent image.
FROM python:3.8-slim

# Install gcc and python3-dev.
RUN apt-get update && \
    apt-get install -y gcc python3-dev

# Install Jupyter using pip.
RUN pip install jupyter

# Install additional packages for your application.
RUN pip install plotly pandas scikit-learn seaborn matplotlib mysql-connector-python pyodbc sqlalchemy

# Set the working directory in the container.
WORKDIR /app

# Copy your application files into the container.
COPY . .

# Expose the port used by Jupyter (default is 8888).
EXPOSE 8888

# Command to start Jupyter notebook.
CMD ["jupyter", "notebook", "--ip='*'", "--port=8888", "--no-browser", "--allow-root"]
