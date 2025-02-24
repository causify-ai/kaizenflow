import pandas as pd
import numpy as np
import load_data

df = load_data.realtime_from_csv()

duplicateCase = df[df.duplicated(['timestamp', 'trade_id', 'amount'], keep=False)]
df.drop_duplicates(subset=["timestamp", "trade_id", "amount"], keep="last", inplace=True)
print(df)