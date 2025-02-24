"""
Compute crypto-related trading volume statistics.

Import as:

import research_amp.cc.volume as ramccvol
"""
import pandas as pd
import seaborn as sns

import core.config.config_ as cconconf
import core.plotting as coplotti


def get_daily_cumul_volume(
    data: pd.DataFrame,
    config: cconconf.Config,
    is_notional_volume: bool,
) -> pd.DataFrame:
    """
    Get daily cumulative volume on (exchange,currency) level.

    :param data: crypto-price data
    :param config: config
    :param is_notional_volume: volume is nominated in US Dollars
    :return: daily cumulative volume per exchange per currency pair
    """
    volume = config["column_names"]["volume"]
    close = config["column_names"]["close"]
    exchange_id = config["column_names"]["exchange"]
    currency_pair = config["column_names"]["currency_pair"]
    if is_notional_volume:
        data[volume] = data[volume] * data[close]
    data["date"] = data.index.date
    data_grouped = data.groupby(
        [exchange_id, currency_pair, "date"], as_index=False
    )
    cumul_daily_volume = data_grouped[volume].sum()
    return cumul_daily_volume


def get_total_exchange_volume(
    data: pd.DataFrame,
    config: cconconf.Config,
    avg_daily: bool,
    display_plot: bool = True,
) -> pd.Series:
    """
    Compute total trading volume by exchange values and plot them on barchart.

    :param data: daily cumulative volume per exchange per currency pair
    :param config: config
    :param avg_daily: volume is normalised by days
    :param display_plot: plot barchart
    :return: total volume by exchange
    """
    volume = config["column_names"]["volume"]
    exchange_id = config["column_names"]["exchange"]
    if avg_daily:
        exchange_volume = data.groupby([exchange_id])[volume].mean()
    else:
        exchange_volume = data.groupby([exchange_id])[volume].sum()
    exchange_volume = exchange_volume.sort_values(ascending=False)
    if display_plot:
        coplotti.plot_barplot(
            exchange_volume,
            title="Total volume per exchange (log-scaled)",
            figsize=[15, 7],
            yscale="log",
        )
    return exchange_volume


def get_total_coin_volume(
    data: pd.DataFrame,
    config: cconconf.Config,
    avg_daily: bool,
    display_plot: bool = True,
) -> pd.Series:
    """
    Compute total trading volume by coins values and plot them on barchart.

    :param data: cumulative volume per exchange per currency pair
    :param config: config
    :param avg_daily: volume is normalised by days
    :param display_plot: plot barchart
    :return: total volume by exchange
    """
    volume = config["column_names"]["volume"]
    currency_pair = config["column_names"]["currency_pair"]
    if avg_daily:
        coin_volume = data.groupby([currency_pair])[volume].mean()
    else:
        coin_volume = data.groupby([currency_pair])[volume].sum()
    coin_volume = coin_volume.sort_values(ascending=False)
    if display_plot:
        coplotti.plot_barplot(
            coin_volume,
            title="Total volume per coin (log-scaled)",
            figsize=[15, 7],
            yscale="log",
        )
    return coin_volume


def get_rolling_volume_per_exchange(
    data: pd.DataFrame,
    config: cconconf.Config,
    window: int,
    display_plot: bool = True,
) -> pd.DataFrame:
    """
    Compute rolling volume by exchange and plot them on graph.

    :param data: daily cumulative volume per exchange per currency pair
    :param config: config
    :param window: number of rolling windows
    :param display_plot: plot graph
    :return: rolling volume by exchange
    """
    volume = config["column_names"]["volume"]
    exchange_id = config["column_names"]["exchange"]
    data_grouped = data.groupby([exchange_id, "date"], as_index=False)
    volume_per_exchange_per_day = data_grouped[volume].sum()
    resampler = volume_per_exchange_per_day.groupby([exchange_id])
    rolling_volume = resampler[volume].transform(
        lambda x: x.rolling(window).mean()
    )
    volume_per_exchange_per_day = volume_per_exchange_per_day.merge(
        rolling_volume.to_frame(), left_index=True, right_index=True
    )
    volume_per_exchange_per_day.rename(
        columns={"volume_x": "volume", "volume_y": "rolling_volume"}, inplace=True
    )
    if display_plot:
        sns.lineplot(
            data=volume_per_exchange_per_day,
            x="date",
            y="rolling_volume",
            hue=exchange_id,
        )
    return volume_per_exchange_per_day


def get_rolling_volume_per_coin(
    data: pd.DataFrame,
    config: cconconf.Config,
    window: int,
    display_plot: bool = True,
) -> pd.DataFrame:
    """
    Compute rolling volume by coins and plot them on graph.

    :param data: daily cumulative volume per exchange per currency pair
    :param config: config
    :param window: number of rolling windows
    :param display_plot: plot graph
    :return: rolling volume by coins
    """
    volume = config["column_names"]["volume"]
    currency_pair = config["column_names"]["currency_pair"]
    data_grouped = data.groupby([currency_pair, "date"], as_index=False)
    volume_per_coin_per_day = data_grouped[volume].sum()
    resampler = volume_per_coin_per_day.groupby([currency_pair])
    rolling_volume = resampler[volume].transform(
        lambda x: x.rolling(window).mean()
    )
    volume_per_coin_per_day = volume_per_coin_per_day.merge(
        rolling_volume.to_frame(), left_index=True, right_index=True
    )
    volume_per_coin_per_day.rename(
        columns={"volume_x": "volume", "volume_y": "rolling_volume"}, inplace=True
    )
    if display_plot:
        sns.lineplot(
            data=volume_per_coin_per_day,
            x="date",
            y="rolling_volume",
            hue=currency_pair,
        )
    return volume_per_coin_per_day


def compare_weekday_volumes(
    data: pd.DataFrame,
    config: cconconf.Config,
    plot_total_volumes: bool = True,
    plot_distr_by_weekdays: bool = True,
) -> pd.Series:
    """
    Compute total volume by weekdays, plot them on barchart and plot
    distribution graphs.

    :param data: daily cumulative volume per exchange per currency pair
    :param config: config
    :param plot_total_volumes: plot barchart
    :param plot_distr_by_weekdays: plot distribution graphs
    :return: rolling volume by coins
    """
    volume = config["column_names"]["volume"]
    data["weekday"] = data["date"].map(lambda x: x.strftime("%A"))
    total_volume_by_weekdays = (
        data.groupby("weekday")[volume].sum().sort_values(ascending=False)
    )
    if plot_total_volumes:
        coplotti.plot_barplot(
            total_volume_by_weekdays,
            title="Total volume per weekdays",
            figsize=[15, 7],
        )
    if plot_distr_by_weekdays:
        weekends = data[
            (data["weekday"] == "Saturday") | (data["weekday"] == "Sunday")
        ]
        weekdays = data[
            (data["weekday"] != "Saturday") & (data["weekday"] != "Sunday")
        ]
        weekends_volume = weekends.groupby(["date", "weekday"])[volume].sum()
        weekdays_volume = weekdays.groupby(["date", "weekday"])[volume].sum()
        sns.displot(weekends_volume).set(title="Volume Distribution by weekends")
        sns.displot(weekdays_volume).set(
            title="Volume Distribution by working days"
        )
    return total_volume_by_weekdays
