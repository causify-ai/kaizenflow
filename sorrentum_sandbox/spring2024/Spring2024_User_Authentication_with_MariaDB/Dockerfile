# Use a small image `alpine` with Python inside.
FROM python:3.8
# Copy current dir `counter_app` into image.


WORKDIR /app

COPY app.py .
# Install requirements.
RUN pip install mysql-connector



# Set the default app.
CMD ["python", "final.py"]
