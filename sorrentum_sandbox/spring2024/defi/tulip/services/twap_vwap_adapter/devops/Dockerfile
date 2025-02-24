FROM python:3.7-slim
RUN mkdir /app
ADD ./twap_vwap_adapter.py /app
WORKDIR /app
RUN pip install flask flask_restful numpy requests gunicorn
EXPOSE 80
ENV FLASK_APP=/app/twap_vwap_adapter.py
# The last element of the array specifies the following key value pair:
#  file:app_var_name, where file is the name of the flask file without the .py extension
#  and app_var_name refers to the variable as defined in the flask file.
CMD ["gunicorn", "--bind", "0.0.0.0:80", "twap_vwap_adapter:app"]


