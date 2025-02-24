import pandas as pd
import numpy as np
import load_data

his_df = load_data.historical_from_csv()

duplicateCase = his_df[his_df.duplicated(['timestamp', 'trade_id', 'amount'], keep=False)]
his_df.drop_duplicates(subset=["timestamp", "trade_id", "amount"], keep="last", inplace=True)
print(his_df)