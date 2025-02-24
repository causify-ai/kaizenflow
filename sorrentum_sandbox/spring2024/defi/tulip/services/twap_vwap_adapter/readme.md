# TWAP VWAP Adapter

## Run container locally

```
> docker run -e API_KEY=test -p 5000:80 --name twap_vwap_adapter 623860924167.dkr.ecr.eu-north-1.amazonaws.com/cmamp:twap_vwap_adapter
```

## Request and response example 

```
> curl -X POST -H "Content-Type: application/json" -H "X-API-KEY: test" -d '{"jobRunID": "42", "symbol": "bitcoin", "start_time": 1681919933, "end_time": 1681920353}' http://localhost:5000/get_twap
```

```
{"data":{"result":"1.6819202140995054e+30"},"jobRunID":"42"}
```

*Note: In order to make the request possible using docker-in-docker, run the above*  `docker run ...` *and* `curl ...` from inside docker