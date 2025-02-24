# """
# Combine Datastream and IDC liquidity data and use it to compute a universe.
#
# Import as:
#
# import vendors_lime.datastream_liquidity.universe_utils as vldlunut
# """
#
# import logging
# from typing import List
#
# import pandas as pd
# from tqdm.autonotebook import tqdm
#
# import helpers.hdatetime as hdateti
# import helpers.hdbg as hdbg
# import helpers.hsql as hsql
# import im_v2.ig.ig_utils as imvigigut
# import im_v2.ig.universe.ticker_igid_mapping as imviutigma
# import vendors_lime.datastream_liquidity.utils as vldaliut
# import vendors_lime.idc.utils as vliiduti
#
# _LOG = logging.getLogger(__name__)
#
#
# def _and_filters(filters: List[pd.Series]) -> pd.Series:
#    """
#    Compute the logical AND of a list of filters, represented by Series.
#
#    :param filters: a list of binary series, each representing a filtering criteria
#    """
#    hdbg.dassert(filters, "`filters` must be nonempty.")
#    and_filter = filters[0]
#    for filter_ in filters:
#        _LOG.debug(
#            "filter on col=%s removes %d (%.2f) of elements in isolation",
#            filter_.name,
#            sum(~filter_),
#            sum(~filter_) / filter_.size,
#        )
#        and_filter = and_filter & filter_
#        _LOG.debug(
#            "Number remaining=%s after applying filter on col=%s in succession",
#            sum(and_filter),
#            filter_.name,
#        )
#    _LOG.info("Number remaining=%s after applying filters", sum(and_filter))
#    return and_filter
#
#
# def _apply_categorical_filters(df: pd.DataFrame) -> pd.DataFrame:
#    """
#    Apply criteria to `df` to select assets that could belong to our universe.
#
#    E.g., we filter out non-US assets.
#    """
#    filters = []
#    # Datastream liquidity columns.
#    filters.append(df["country"] == "US")
#    filters.append(df["currency"] == "USD")
#    filters.append(df["is_major_sec"] == True)
#    # Primary vs collateral security.
#    filters.append(df["is_prim_qt"] == True)
#    # IDC column.
#    # On 2022-03-01
#    # NA:C     5536     -> Stocks
#    # NA:F     3383     -> ETFs
#    # NA:W      977     -> Warrants
#    # NA:U      739
#    # NA:P      574
#    # NA:A      466
#    # NA:I      408
#    # NA:R       53
#    # NA:S       31
#    # TODO(gp): Remove the space at the end.
#    # filters.append(df["sectype"] == "NA:C ")
#    filters.append(df["sectype"] == "NA:F ")
#    # Filter.
#    filter_ = _and_filters(filters)
#    filtered_df = df[filter_].copy()
#    return filtered_df
#
#
# def generate_liquidity_df(
#    datetime_: hdateti.Datetime,
#    connection: hsql.DbConnection,
#    *,
#    apply_categorical_filters: bool = True,
#    add_rankings: bool = True,
# ) -> pd.DataFrame:
#    """
#    Create a merged Datastream / IDC liquidity dataframe.
#
#    Some interesting columns are:
#    - asset_id
#    - ticker
#    - is_major_sec: major security
#    - is_prim_qt: primary vs collateral
#    - last_close
#    - spread
#    - mdv shares / usd
#    - close_ct: ?
#    - bd_ct: ?
#    - volume:?
#    - sec_type: class of security (e.g., stock, ETFs)
#    - mkt_cap
#
#    :param datetime_: year, month, day
#    :param connection: connection to IDC database
#    """
#    hdateti.dassert_is_datetime(datetime_)
#    date = hdateti.to_datetime(datetime_)
#    # Get IDC data.
#    asset_ids = None
#    df = vldaliut.get_liquidity_data(asset_ids, [date])
#    # Load ticker / asset_id mapping.
#    ig_date = imvigigut.convert_to_ig_date(date)
#    id_mapping = imviutigma.get_id_mapping(ig_date)
#    # Add tickers.
#    # TODO(gp): Maybe use prefix like `ds_` and `idc_` to distinguish the columns.
#    df = df.merge(id_mapping, how="left", on="asset_id")
#    # Add market cap.
#    market_cap = df["num_shrs"] * df["last_close_usd"]
#    df["market_cap"] = market_cap
#    # Add IDC data.
#    idc_df = vliiduti.get_idc_data(datetime_, connection)
#    df = df.merge(
#        idc_df, on=["region", "trade_date", "asset_id", "country"], how="outer"
#    )
#    # Apply categorical filters.
#    if apply_categorical_filters:
#        df = _apply_categorical_filters(df)
#    # Compute percentage ranks of some columns.
#    if add_rankings:
#        datastream_liquidity_cols_to_rank = [
#            "spread_bps_21d",
#            "spread_bps_42d",
#            "spread_bps_63d",
#            "spread_usd_21d",
#            "spread_usd_42d",
#            "spread_usd_63d",
#            "mdv_shares_21d",
#            "mdv_shares_42d",
#            "mdv_shares_63d",
#            "mdv_usd_21d",
#            "mdv_usd_42d",
#            "mdv_usd_63d",
#        ]
#        derived_cols_to_rank = [
#            "market_cap",
#        ]
#        idc_cols_to_rank = ["mkt_cap_usd_avg_90d"]
#        cols_to_rank = (
#            datastream_liquidity_cols_to_rank
#            + derived_cols_to_rank
#            + idc_cols_to_rank
#        )
#        ranked_df = df[cols_to_rank].rank(pct=True)
#        # Add percentage ranks to dataframe.
#        df = df.merge(
#            ranked_df, left_index=True, right_index=True, suffixes=(None, "_pct")
#        )
#    return df
#
#
## #############################################################################
#
#
# def apply_threshold_filters(
#    df: pd.DataFrame,
#    min_last_close_usd: float = 10,
#    min_mdv_usd_63d_pct: float = 0.5,
#    min_mkt_cap_usd_avg_90d_pct: float = 0.5,
#    max_spread_bps_63d_pct: float = 0.5,
#    max_count: int = 1000,
# ) -> pd.DataFrame:
#    """
#    Apply criteria to select assets that are candidates for the universe.
#    """
#    filters = []
#    # Datastream liquidity-derived columns.
#    filters.append(df["last_close_usd"] > min_last_close_usd)
#    filters.append(df["spread_bps_63d_pct"] < max_spread_bps_63d_pct)
#    filters.append(df["mdv_usd_63d_pct"] > min_mdv_usd_63d_pct)
#    # IDC-derived column.
#    filters.append(df["mkt_cap_usd_avg_90d_pct"] > min_mkt_cap_usd_avg_90d_pct)
#    # Filter.
#    filter_ = _and_filters(filters)
#    filtered_df = df[filter_]
#    # Max count filter.
#    max_count_idx = filtered_df["spread_bps_63d_pct"].nsmallest(max_count).index
#    filtered_df = filtered_df.loc[max_count_idx]
#    return filtered_df
#
#
# def get_filtered_universe_dfs(
#    datetimes: List[hdateti.Datetime], connection: hsql.DbConnection
# ) -> List[pd.DataFrame]:
#    """
#    Create a list of dataframes, one per date, with the universe on that date.
#    """
#    dfs = []
#    for datetime_ in tqdm(datetimes):
#        try:
#            df = generate_liquidity_df(datetime_, connection)
#        except OSError:
#            _LOG.warning("Unable to generate universe on date=%s", datetime_)
#            continue
#        # Filter based on the selection criteria.
#        df = apply_threshold_filters(df)
#        df = df[["trade_date", "asset_id", "ticker"]].sort_values("ticker")
#        hdbg.dassert_eq(
#            1,
#            df["trade_date"].nunique(),
#            "Dataframe has multiple `trade_date` values=%s",
#            df["trade_date"].unique(),
#        )
#        hdbg.dassert(
#            not df.duplicated(subset=["asset_id"]).any(),
#            "Dataframe contains duplicate `asset_id` data",
#        )
#        df = df.reset_index(drop=True)
#        dfs.append(df)
#    return dfs
#
#
# def combine_universe_dfs(dfs: List[pd.DataFrame]) -> pd.DataFrame:
#    """ """
#
#    processed = []
#    for df in tqdm(dfs):
#        srs = pd.Series(
#            index=df["asset_id"], data=True, name=df["trade_date"].iloc[0]
#        )
#        processed.append(srs)
#    out_df = pd.concat(processed, axis=1).fillna(False)
#    hdbg.dassert(not out_df.index.has_duplicates, "Duplicate asset_ids detected")
#    hdbg.dassert(not out_df.columns.has_duplicates, "Duplicate dates detected")
#    return out_df.transpose()
