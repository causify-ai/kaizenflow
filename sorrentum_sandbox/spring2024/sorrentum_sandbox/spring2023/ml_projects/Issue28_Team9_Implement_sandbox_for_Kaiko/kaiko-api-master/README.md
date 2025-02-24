# Kaiko API
A python wrapper to use Kaiko's data API.
Please note that this repository is not officially maintained by Kaiko, contributions are welcome!

## Notes on this version 

For the current implementation: Valuation and DEXLiquidityEvents and DexLiquiditySnapshots are not stable yet.

### Importing the API to a project

Available from PyPi via a ``` pip install kaiko ``` 
```python
import kaiko
```

### Example 1: Getting some candles (Count OHLCV VWAP)


Create a data store from the class Candles.  The example below downloads all the daily 
candles for BTC/USD on LMAX from August 2020 and stores it into the attribute `df`:
```python
# Setting a client with your API key
kc = kaiko.KaikoClient(api_key='<YOUR_API_KEY_HERE>')

# Getting some simple daily candles
ds = kaiko.Aggregates(type_of_aggregate = 'COHLCV_VWAP', exchange = 'cbse', instrument = 'btc-usdt', start_time='2020-08', interval='1d', client=kc)

# Retrieve the dataframe containing the data
ds.df
```
```buildoutcfg
               open       high      low  ...    volume         price    count
timestamp                                ...                                 
2020-08-01  11349.0  11894.499  11236.0  ...   9581.14  11628.811655  14592.0
2020-08-02  11809.5  12138.500  10506.0  ...  13111.98  11298.557532  20580.0
2020-08-03  11080.5  11486.500  10930.0  ...   7577.23  11250.357069  14669.0
2020-08-04  11236.5  11423.000  10987.0  ...   6048.70  11212.375852  10993.0
2020-08-05  11195.5  11801.000  11078.5  ...   7185.89  11504.596981  14105.0
2020-08-06  11758.5  11916.000  11580.0  ...   8281.78  11763.846493  18411.0
2020-08-07  11773.5  11925.000  11750.5  ...   1407.75  11845.449098   2851.0
```

The datastore takes parameters in accordance to the documentation found at https://docs.kaiko.com/. The date format is flexible and is translated from a pandas datetime format to the native format of the API.
