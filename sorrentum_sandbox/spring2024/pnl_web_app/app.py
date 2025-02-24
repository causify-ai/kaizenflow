#!/usr/bin/env python
# TODO(Grisha): consider discontinuing the flow as we have more powerful tools,
# e.g., grafana, see CmTask7916.
"""
Dash app for displaying PnL.

Usage:
> python oms/pnl_web_app/app.py
"""
import datetime
import functools
import logging
import math
import os
from typing import Dict

import dash
import dash.dependencies as dash_deps
import dash_bootstrap_components as dbc
import pandas as pd
import pytz

import dataflow.model as dtfmod
import helpers.hio as hio
import helpers.hpandas as hpandas
import im_v2.common.universe as ivcu
import reconciliation as reconcil

DEFAULT_START_DATE = datetime.datetime(2019, 9, 1)

_LOG = logging.getLogger(__name__)

dbc_css = (
    "https://cdn.jsdelivr.net/gh/AnnMarieW/dash-bootstrap-templates/dbc.min.css"
)

APP_THEME = dbc.themes.MORPH
DEBUG_MODE = os.environ.get("DASH_DEBUG_MODE", "1") == "1"
BASE_PATH = "/shared_data/ecs/preprod/system_reconciliation/C3a"
# See the TODO comment in `obrbrexa.get_DataFrameBroker_example1()`.
UNIVERSE_VERSION = ivcu.get_latest_universe_version()
# Because ECS container only see past /data/shared/ecs There is a softlink:
# ln -s /data/shared/model/historical/pnl_for_website/ /data/shared/ecs/pnl_for_website
HISTORICAL_PATH = (
    "/shared_data/ecs/pnl_for_website"
    f"/build_tile_configs.C3a.ccxt_{UNIVERSE_VERSION.replace('.', '_')}-all.5T.2019-09-01_2023-05-15.ins"
    "/tiled_results/"
)
PATH_POSTFIX = "process_forecasts/portfolio"


def _map_asset_id_cols_to_symbols(trades: pd.DataFrame) -> pd.DataFrame:
    """
    Map DataFrame with columns represented by asset IDs to symbol columns.
    """
    full_symbol_universe = ivcu.get_vendor_universe(
        "CCXT", "trade", version=UNIVERSE_VERSION, as_full_symbol=True
    )
    full_symbol_universe = list(
        # For now only binance is used.
        filter(lambda s: s.startswith("binance"), full_symbol_universe)
    )
    # Build asset_id -> symbol mapping.
    asset_id_to_full_symbol_mapping = ivcu.build_numerical_to_string_id_mapping(
        full_symbol_universe
    )
    trades = trades.rename(columns=asset_id_to_full_symbol_mapping)
    return trades


def get_next_time_of_refresh(
    delta: datetime.timedelta = None,
) -> datetime.datetime:
    """
    Get the next time of refresh based on the current time.

    :param delta: time delta between refreshes
    :return: next time of refresh
    """
    one_minute = datetime.timedelta(minutes=1)
    if not delta:
        delta = datetime.timedelta(minutes=5)
    now = datetime.datetime.now()
    # Round down to the nearest delta interval + one minute.
    # One minute is added because the actual refresh will happen about 40 seconds
    # after the scheduled time.
    rounded_datetime = (
        datetime.datetime.min
        + math.floor((now - datetime.datetime.min) / delta) * delta
        + one_minute
    )
    # If the rounded time is in the past, add another delta interval.
    if rounded_datetime < now:
        rounded_datetime += delta
    return rounded_datetime


def _get_pnl_path(pnl_date: datetime.datetime) -> str:
    """
    Get the path to the PnL directory for a given date.

    :param path_date: date in the format YYYYMMDD
    :return: path to the PnL directory
    """
    tz = pytz.timezone("UTC")
    if not pnl_date:
        pnl_date = datetime.datetime.now(tz)
    # If the current time is before 1:15 PM UTC, then use the previous day
    # as run start date, the current daily run schedule is 1PM UTC (the run starts 10 minutes later)
    # after the Airflow DAG is scheduled
    # TODO(Juraj): Make this more universal.
    now = datetime.datetime.now(tz)
    today_start_time = now.replace(hour=13, minute=15)
    if now < today_start_time:
        pnl_date = pnl_date - datetime.timedelta(days=1)
    path_date = pnl_date.strftime("%Y%m%d")
    only_files = False
    use_relative_paths = False
    # Scan the base path for the date folder.
    folder_list = hio.listdir(
        BASE_PATH, path_date, only_files, use_relative_paths
    )
    if len(folder_list) == 0:
        raise ValueError(f"Could not find a folder for date {path_date}")
    second_path = folder_list[0]
    pattern = "system_log_dir.scheduled*"
    # Scan the date folder for the PnL folder.
    second_folder_list = hio.listdir(
        second_path, pattern, only_files, use_relative_paths
    )
    if len(second_folder_list) == 0:
        raise ValueError(f"Could not find a folder for date {path_date}")
    return os.path.join(second_folder_list[0], PATH_POSTFIX)


def get_last_trades_dict(pnl_date: datetime.datetime) -> Dict:
    """
    Get the last placed trades.
    """
    portfolio_dir = _get_pnl_path(pnl_date)
    portfolio_df, _ = reconcil.load_portfolio_artifacts(portfolio_dir)
    executed_trades_notional = portfolio_df["executed_trades_notional"]
    # Executed trades for the last bar are stored in the last row.
    executed_trades_notional_current_bar = executed_trades_notional.tail(1)
    executed_trades = _map_asset_id_cols_to_symbols(
        executed_trades_notional_current_bar
    )
    executed_trades = executed_trades.stack().reset_index().round(2)
    executed_trades.columns = [
        "timestamp",
        "Currency pair",
        "Notional price (USDT)",
    ]
    executed_trades = executed_trades[["Currency pair", "Notional price (USDT)"]]
    return executed_trades.to_dict("records")


def get_historical_pnl(
    start_date: datetime.datetime = None, end_date: datetime.datetime = None
) -> pd.DataFrame:
    """
    Get the historical PnL.

    :param start_date: date from which to get the historical PnL
    :param end_date: date until which to get the historical PnL
    :return: historical PnL as a pandas DataFrame
    """
    if not start_date:
        start_date = DEFAULT_START_DATE
    if not end_date:
        end_date = datetime.datetime.now()
    # Load data.
    asset_id_col = "asset_id"
    data_cols = {
        "price": "vwap",
        "volatility": "garman_klass_vol",
        "prediction": "feature",
    }
    data_cols_list = list(data_cols.values())
    iter_ = dtfmod.yield_processed_parquet_tiles_by_year(
        HISTORICAL_PATH,
        start_date,
        end_date,
        asset_id_col,
        data_cols_list,
        asset_ids=None,
    )
    df_res = hpandas.get_df_from_iterator(iter_)
    # Initialize ForecastEvaluatorFromPrices
    fep = dtfmod.ForecastEvaluatorFromPrices(
        data_cols["price"],
        data_cols["volatility"],
        data_cols["prediction"],
    )
    # Compute research portfolio
    _, bar_metrics = fep.annotate_forecasts(
        df_res,
        quantization=30,
        burn_in_bars=3,
        style="longitudinal",
        liquidate_at_end_of_day=False,
        initialize_beginning_of_day_trades_to_zero=False,
    )
    # Extract PnL from the portfolio DataFrame
    cumul_pnl = bar_metrics["pnl"].resample("D").sum(min_count=1).cumsum()
    return cumul_pnl


def get_cumulative_pnl(pnl_date: datetime.datetime = None) -> pd.Series:
    """
    Get the cumulative PnL for a given date.

    :param pnl_date: date which PnL to get
    :return: cumulative PnL as a pandas Series
    """
    path = _get_pnl_path(pnl_date)
    _, stats_df = reconcil.load_portfolio_artifacts(path)
    return stats_df["pnl"].cumsum() * 1000


def get_dash_figure(dataset: pd.DataFrame) -> dict:
    """
    Get the figure for the PnL plot.

    :param dataset: dataset to plot
    :return: figure for the PnL plot as a dict
    """
    figure = {
        "data": [
            {
                "x": dataset.index,
                "y": dataset.values,
                "type": "lines",
            }
        ],
        "layout": {"yaxis": {"tickprefix": "$"}},
    }
    return figure


app = dash.Dash(__name__, external_stylesheets=[APP_THEME, dbc_css])

header = dash.html.H4(
    "Crypto-Kaizen PnL graphs",
    className="bg-primary text-white p-2 mb-2 text-center",
)


def add_warning_to_content(func):
    """
    Add a warning message to the content if an error occurs.

    :param func: function to wrap
    :return: wrapped function
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
        except Exception as e:
            return dbc.Alert(
                f"Error: {e}",
                color="warning",
            )
        return result

    return wrapper


@add_warning_to_content
def get_last_trades_table() -> dash.dash_table.DataTable:
    """
    Get the current PnL graph.
    """
    return dash.dash_table.DataTable(
        get_last_trades_dict(datetime.datetime.now()),
        id="last_trades",
        style_as_list_view=True,
        fill_width=True,
        style_header={"fontWeight": "bold"},
        style_data_conditional=[
            {
                "if": {"row_index": "odd"},
                "backgroundColor": "rgb(220, 220, 220)",
            }
        ],
        style_table={"height": "500px", "overflowY": "auto"},
    )


@add_warning_to_content
def get_current_pnl_graph() -> dash.dcc.Graph:
    """
    Get the current PnL graph.
    """
    return dash.dcc.Graph(
        id="current_pnl",
        figure=get_dash_figure(get_cumulative_pnl(datetime.datetime.now())),
    )


row_last_pnl = dbc.Row(
    [
        dbc.Col([get_last_trades_table()], width=4),
        dbc.Col([get_current_pnl_graph()], width=8),
    ]
)

tab_last_pnl = dbc.Tab(
    [row_last_pnl], label="Trades and Cumulative PnL for the last 5 minutes"
)


@add_warning_to_content
def get_yesterday_pnl_graph() -> dash.dcc.Graph:
    """
    Get the PnL graph for the last 24 hours.
    """
    return dash.dcc.Graph(
        id="yesterday_pnl",
        figure=get_dash_figure(
            get_cumulative_pnl(
                datetime.datetime.now() - datetime.timedelta(days=1)
            )
        ),
    )


tab_yesterday = dbc.Tab(
    [get_yesterday_pnl_graph()], label="Cumulative PnL last 24 hours"
)


@add_warning_to_content
def get_pnl_since_2022_graph() -> dash.dcc.Graph:
    """
    Get the PnL graph since 2022.
    """
    return dash.dcc.Graph(
        id="pnl_since_2022",
        figure=get_dash_figure(
            get_historical_pnl(
                start_date=datetime.datetime(2022, 1, 1),
            )
        ),
    )


tab_since_2022 = dbc.Tab(
    [get_pnl_since_2022_graph()], label="Cumulative PnL since 2022"
)


@add_warning_to_content
def get_pnl_since_2019_graph() -> dash.dcc.Graph:
    """
    Get the PnL graph since 2019.
    """
    return dash.dcc.Graph(
        id="pnl_since_2019",
        figure=get_dash_figure(
            get_historical_pnl(
                start_date=DEFAULT_START_DATE,
            )
        ),
    )


tab_since_2019 = dbc.Tab(
    [get_pnl_since_2019_graph()], label="Cumulative PnL since 2019"
)
tabs = dbc.Card(
    dbc.Tabs(
        [
            tab_last_pnl,
            tab_yesterday,
            tab_since_2022,
            tab_since_2019,
        ]
    )
)
info_card = dbc.Card(
    dbc.ListGroup(
        [
            dbc.ListGroupItem(
                "Next refresh countdown: ", id="countdown_next_refresh"
            ),
            dbc.ListGroupItem("Next refresh: ", id="next_refresh_datetime"),
            dbc.ListGroupItem("Last refresh: ", id="last_refresh_datetime"),
        ],
        flush=True,
    ),
    # style={"width": "18rem"},
)

# Main layout component.
app.layout = dash.html.Div(
    [
        header,
        info_card,
        tabs,
        dash.dcc.Interval(id="1-second-interval", interval=1000, n_intervals=0),
        dash.dcc.Interval(
            id="5-minute-interval", interval=1000 * 300, n_intervals=0
        ),
    ]
)


@app.callback(
    dash_deps.Output("current_pnl", "figure"),
    dash_deps.Output("last_trades", "data"),
    dash_deps.Output("last_refresh_datetime", "children"),
    dash_deps.Input("5-minute-interval", "n_intervals"),
)
def update_layout(n):
    return (
        get_dash_figure(get_cumulative_pnl(datetime.datetime.now())),
        get_last_trades_dict(datetime.datetime.now()),
        f"Last refresh: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )


@app.callback(
    [
        dash_deps.Output("countdown_next_refresh", "children"),
        dash_deps.Output("next_refresh_datetime", "children"),
    ],
    [dash_deps.Input("1-second-interval", "n_intervals")],
)
def update_countdown(n):
    next_time_of_refresh = get_next_time_of_refresh()
    delta = next_time_of_refresh - datetime.datetime.now()
    return (
        f"Next refresh countdown: {delta.seconds // 60} min: {delta.seconds % 60} sec",
        f"Next refresh: {next_time_of_refresh.strftime('%Y-%m-%d %H:%M:%S')}",
    )


if __name__ == "__main__":
    app.run_server(debug=DEBUG_MODE, host="0.0.0.0", port=80)
