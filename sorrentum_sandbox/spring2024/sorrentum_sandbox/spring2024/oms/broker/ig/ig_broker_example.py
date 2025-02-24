# """
# Import as:
#
# import oms.broker.ig.ig_broker_example as obiibrex
# """
#
# import asyncio
#
# import helpers.hasyncio as hasynci
# import market_data as mdata
# import oms.broker.ig.ig_broker as obigigbr
#
# # TODO(gp): @all ig_broker -> IgBroker, example1 -> prod_instance1 or just instance1
# def get_ig_broker_example1(
#     # TODO(gp): Remove event_loop.
#     event_loop: asyncio.AbstractEventLoop,
#     # TODO(gp): This needs to be of IgSql...
#     market_data: mdata.MarketData,
#     *,
#     # TODO(gp): These should be exposed without default values.
#     strategy_id: str = "SAU1",
#     liveness: str = "CANDIDATE",
#     instance_type: str = "QA",
# ) -> obigigbr.IgBroker:
#     """
#     Build an `IgBroker`.
#     """
#     # TODO(gp): event_loop is not needed for IG since there is only real real-time.
#     _ = event_loop
#     # Build IgBroker.
#     get_wall_clock_time = market_data.get_wall_clock_time
#     poll_kwargs = hasynci.get_poll_kwargs(get_wall_clock_time, timeout_in_secs=60)
#     timestamp_col = "end_time"
#     broker = obigigbr.IgBroker(
#         strategy_id,
#         market_data,
#         liveness=liveness,
#         instance_type=instance_type,
#         poll_kwargs=poll_kwargs,
#         timestamp_col=timestamp_col,
#     )
#     return broker
