FROM python:3

# Installing system dependencies
RUN apt-get update && \
    apt-get install -y \
        redis-server \
        sqlite3 \
        curl

# Installing libaries needed for project
RUN pip install pandas redis plotly seaborn matplotlib SQLAlchemy jupyter

# copying project files
COPY . /notebooks
WORKDIR /notebooks

# Jupyter notebook port
EXPOSE 8888

# Running jupyter notebook
CMD ["jupyter", "notebook", "--ip='*'", "--port=8888", "--no-browser", "--allow-root"]
