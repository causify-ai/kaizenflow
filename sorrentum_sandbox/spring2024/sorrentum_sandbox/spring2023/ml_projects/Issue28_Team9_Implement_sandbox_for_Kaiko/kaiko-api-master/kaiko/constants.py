"""
Constants for the wrapper

"""
# Base URLs

_BASE_URL_KAIKO_US = "https://us.market-api.kaiko.io/"
_BASE_URL_KAIKO_EU = "https://eu.market-api.kaiko.io/"
_BASE_URL_RAPIDAPI = "https://kaiko-cryptocurrency-market-data.p.rapidapi.com/"  # Not supported yet
_BASE_URLS = dict(
    us=_BASE_URL_KAIKO_US, eu=_BASE_URL_KAIKO_EU, rapidapi=_BASE_URL_RAPIDAPI
)

################################################# API endpoints #######################################
_URL_REFERENCE_DATA_API = "https://reference-data-api.kaiko.io/v1/"

#### Trade data ####

_URL_TRADE_HISTORICAL_TRADES = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}"
    "/trades"
)

#### Order book data ####

_URL_ORDER_BOOK_SNAPSHOTS_FULL = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}"
    "/snapshots/full"
)
_URL_ORDER_BOOK_SNAPSHOTS_RAW = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}"
    "/snapshots/raw"
)
_URL_ORDER_BOOK_SNAPSHOTS_DEPTH = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}"
    "/snapshots/depth"
)
_URL_ORDER_BOOK_SNAPSHOTS_SLIPPAGE = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}"
    "/snapshots/slippage"
)

_URL_ORDER_BOOK_AGGREGATIONS_FULL = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}"
    "/{instrument}/ob_aggregations/full"
)
_URL_ORDER_BOOK_AGGREGATIONS_DEPTH = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}"
    "/ob_aggregations/depth"
)
_URL_ORDER_BOOK_AGGREGATIONS_SLIPPAGE = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}"
    "/ob_aggregations/depth"
)

#### Aggregates data ####
_URL_AGGREGATES_OHLCV = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}/aggregations"
    "/ohlcv"
)
_URL_AGGREGATES_VWAP = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}/aggregations"
    "/vwap"
)
_URL_AGGREGATES_COHLCV_VWAP = (
    "v2/data/{commodity}.{data_version}/exchanges/{exchange}/{instrument_class}/{instrument}/aggregations"
    "/count_ohlcv_vwap"
)

#### Pricing and valuation data ####

_URL_PRICING_SPOT_DIRECT_EXCHANGE_RATE = "v2/data/trades.{data_version}/spot_direct_exchange_rate/{base_asset}/{quote_asset}"
_URL_PRICING_SPOT_EXCHANGE_RATE = (
    "v2/data/trades.{data_version}/spot_exchange_rate/{base_asset}/{quote_asset}"
)
_URL_PRICING_VALUATION = "v2/data/trades.{data_version}/valuation"

#### DEX liquidity data ####

_URL_DEX_LIQUIDITY_EVENTS = "v2/data/liquidity.v1/events"
_URL_DEX_LIQUIDITY_SNAPSHOTS = "v2/data/liquidity.v1/snapshots"


#### Risk management data ####

_URL_RISK_VALUE_AT_RISK = (
    "v2/data/analytics.v2/value_at_risk?bases={bases}&exchanges={exchanges}&quantities={quantities}&quote={quote}&risk_level={risk_level}&"
    "start_time={start_time}&end_time={end_time}&sources={sources}"
)

#### Reference data ####

_URL_DERIVATIVES_REFERENCE = "v2/data/derivatives.v2/reference"
_URL_DERIVATIVES_RISK = "v2/data/derivatives.v2/risk"
_URL_DERIVATIVES_PRICE = "v2/data/derivatives.v2/price"
