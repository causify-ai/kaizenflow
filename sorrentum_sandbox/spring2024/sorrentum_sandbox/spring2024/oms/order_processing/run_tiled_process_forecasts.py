"""
This is the library backing `run_process_forecasts.py`.

Import as:

import oms.order_processing.run_tiled_process_forecasts as ooprtprfo
"""
import asyncio
import logging
from typing import Any, Dict

import pandas as pd
from tqdm.autonotebook import tqdm

import helpers.hdbg as hdbg
import helpers.hpandas as hpandas
import helpers.hparquet as hparque
import market_data as mdata
import oms.order_processing.process_forecasts_ as oopprfo
import oms.portfolio.portfolio as oporport
import oms.portfolio.portfolio_example as opopoexa

_LOG = logging.getLogger(__name__)

# TODO(Paul): @all Move to portfolio_example.py
def get_portfolio(market_data: mdata.MarketData) -> oporport.Portfolio:
    strategy_id = "strategy"
    account = "account"
    timestamp_col = "end_time"
    mark_to_market_col = "close"
    pricing_method = "twap.5T"
    initial_holdings = pd.Series([0], [-1])
    column_remap = {
        "bid": "bid",
        "ask": "ask",
        "price": "close",
        "midpoint": "midpoint",
    }
    portfolio = opopoexa.get_DataFramePortfolio_example2(
        strategy_id,
        account,
        market_data,
        timestamp_col,
        mark_to_market_col,
        pricing_method,
        initial_holdings,
        column_remap=column_remap,
    )
    return portfolio


# TODO(gp): Move this to `run_process_forecasts.py`.
async def run_tiled_process_forecasts(
    event_loop: asyncio.AbstractEventLoop,
    market_data_tile_dict: Dict[str, Any],
    backtest_tile_dict: Dict[str, Any],
    process_forecasts_dict: Dict[str, Any],
) -> oporport.Portfolio:
    hdbg.dassert_isinstance(market_data_tile_dict, Dict)
    hdbg.dassert_isinstance(backtest_tile_dict, Dict)
    hdbg.dassert_isinstance(process_forecasts_dict, Dict)
    # Process `backtest_tile_dict`.
    backtest_file_name = backtest_tile_dict["file_name"]
    asset_id_col = backtest_tile_dict["asset_id_col"]
    start_date = backtest_tile_dict["start_date"]
    end_date = backtest_tile_dict["end_date"]
    prediction_col = backtest_tile_dict["prediction_col"]
    volatility_col = backtest_tile_dict["volatility_col"]
    spread_col = backtest_tile_dict["spread_col"]
    # Yield backtest tiles.
    backtest_cols = [asset_id_col, volatility_col, prediction_col, spread_col]
    backtest_tiles = hparque.yield_parquet_tiles_by_year(
        backtest_file_name,
        start_date,
        end_date,
        backtest_cols,
    )
    # Process `market_data_tile_dict`.
    market_data_file_name = market_data_tile_dict["file_name"]
    price_col = market_data_tile_dict["price_col"]
    knowledge_datetime_col = market_data_tile_dict["knowledge_datetime_col"]
    start_time_col = market_data_tile_dict["start_time_col"]
    end_time_col = market_data_tile_dict["end_time_col"]
    # Yield market data tiles.
    market_data_cols = [
        asset_id_col,
        price_col,
        knowledge_datetime_col,
        start_time_col,
        end_time_col,
    ]
    market_data_cols = list(set(market_data_cols))
    market_data_tiles = hparque.yield_parquet_tiles_by_year(
        market_data_file_name,
        start_date,
        end_date,
        market_data_cols,
    )
    # Process forecasts by tile.
    num_years = end_date.year - start_date.year + 1
    for backtest_tile in tqdm(backtest_tiles, total=num_years):
        # Parquet reads asset_ids as categoricals; convert to ints.
        backtest_tile = hpandas.convert_col_to_int(backtest_tile, asset_id_col)
        # Convert any dataframe columns to ints if possible.
        backtest_tile = backtest_tile.rename(columns=hparque.maybe_cast_to_int)
        # Build a `MarketData` object from `market_data_tile`.
        market_data_tile = next(market_data_tiles)
        market_data_tile = hpandas.convert_col_to_int(
            market_data_tile, asset_id_col
        )
        market_data_tile.index.name = end_time_col
        market_data_tile = market_data_tile.reset_index()
        market_data, _ = mdata.get_ReplayedTimeMarketData_from_df(
            event_loop,
            5,
            market_data_tile,
            knowledge_datetime_col_name=knowledge_datetime_col,
            asset_id_col_name=asset_id_col,
            start_time_col_name=start_time_col,
            end_time_col_name=end_time_col,
        )
        # TODO(Paul): Initialize `portfolio` from state from previous loop.
        portfolio = get_portfolio(market_data)
        # Extract the prediction and volatility data as dataframes with columns
        # equal to asset ids.
        prediction_df = backtest_tile[[prediction_col, asset_id_col]].pivot(
            columns=asset_id_col,
            values=prediction_col,
        )
        volatility_df = backtest_tile[[volatility_col, asset_id_col]].pivot(
            columns=asset_id_col,
            values=volatility_col,
        )
        spread_df = backtest_tile[[spread_col, asset_id_col]].pivot(
            columns=asset_id_col,
            values=spread_col,
        )
        restrictions_df = None
        await oopprfo.process_forecasts(
            prediction_df,
            volatility_df,
            portfolio,
            process_forecasts_dict,
            spread_df=spread_df,
            restrictions_df=restrictions_df,
        )
        # TODO(Paul): Save `portfolio` state.
    return portfolio
