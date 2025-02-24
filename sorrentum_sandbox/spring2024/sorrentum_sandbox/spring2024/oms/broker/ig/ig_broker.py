# """
# Import as:
#
# import oms.broker.ig.ig_broker as obigigbr
# """
#
# import collections
# import datetime
# import logging
# import os
# from typing import Any, Dict, List, Optional
#
# import numpy as np
# import pandas as pd
#
# import helpers.hdbg as hdbg
# import helpers.hio as hio
# import helpers.hpandas as hpandas
# import helpers.hprint as hprint
# import helpers.hsystem as hsystem
# import oms
# import vendors_lime.ig_credentials as vliegcre
#
# _LOG = logging.getLogger(__name__)
#
#
# def _cast_to_int(obj: Any) -> int:
#     as_int = int(obj)
#     # hdbg.dassert_eq(obj, as_int)
#     return as_int
#
#
# class IgBroker(oms.DatabaseBroker):
#     """
#     IG implementation of the interface to place orders and receive back fills.
#
#     This implementation is the same as a broker using a mocked DB but
#     using a real DB.
#     """
#
#     def __init__(
#         self,
#         *args: Any,
#         liveness: str,
#         instance_type: str,
#         # TODO(gp): Use the same idiom of IgPortfolio passing `log_dir` to write
#         #  the orders.
#         poll_kwargs: Optional[Dict[str, Any]] = None,
#         **kwargs: Dict[str, Any],
#     ):
#         """
#         Constructor.
#
#         :param strategy_id: e.g., SAU1
#         """
#         vliegcre.dassert_is_config_valid(liveness, instance_type)
#         self._liveness = liveness
#         self._instance_type = instance_type
#         # For IG we don't need an account.
#         account = None
#         account_type = vliegcre.get_core_db_postfix(
#             self._liveness, self._instance_type
#         )
#         db_connection = vliegcre.get_rt_db_connection(account_type)
#         # In `IgBroker` orders are submitted through an S3 directory and not through
#         # a DB table, so we use a dummy table.
#         submitted_orders_table_name = "dummy_table"
#         # In `IgBroker` the name of the table depends on the type of account,
#         # E.g., "target_files_processed_candidate_view"
#         accepted_orders_table_name = vliegcre.get_core_db_view(
#             "target_files_processed", liveness, instance_type
#         )
#         super().__init__(
#             *args,
#             account=account,
#             db_connection=db_connection,
#             submitted_orders_table_name=submitted_orders_table_name,
#             accepted_orders_table_name=accepted_orders_table_name,
#             poll_kwargs=poll_kwargs,
#             **kwargs,
#         )
#
#     @property
#     def liveness(self) -> str:
#         return self._liveness
#
#     @property
#     def instance_type(self) -> str:
#         return self._instance_type
#
#     @property
#     def db_connection(self) -> str:
#         return self._db_connection
#
#     @staticmethod
#     def _get_S3_tradelist_path(liveness: str, instance_type: str) -> str:
#         vliegcre.dassert_is_config_valid(liveness, instance_type)
#         if instance_type != "PROD":
#             drop_id = "qa"
#         elif liveness != "LIVE":
#             drop_id = "cand"
#         else:
#             drop_id = "prod"
#         # TODO(gp): We should also support listType=universeDropout (see pynudge
#         #  Java code).
#         return drop_id
#
#     async def _submit_orders(
#         self,
#         orders: List[oms.Order],
#         wall_clock_timestamp: pd.Timestamp,
#         *,
#         dry_run: bool = False,
#     ) -> str:
#         """
#         Same as abstract class.
#
#         :return: a `file_name` representing the id of the submitted order in the DB
#         """
#         _LOG.info("\n%s", hprint.frame("Sending order"))
#         _LOG.info("orders=%s", orders)
#         # Create df for all the orders.
#         dfs = []
#         hdbg.dassert_container_type(orders, list, oms.Order)
#         for order in orders:
#             asset_id = order.asset_id
#             # TODO(gp): Here we should only have ints already. For now we cast them.
#             curr_position_in_shares = _cast_to_int(order.curr_num_shares)
#             diff_position_in_shares = _cast_to_int(order.diff_num_shares)
#             if diff_position_in_shares == 0:
#                 _LOG.debug(
#                     "Skipping order %s after casting to int diff_num_shares",
#                     str(order),
#                 )
#                 continue
#             df_tmp = self._convert_order_to_df(
#                 wall_clock_timestamp,
#                 asset_id,
#                 curr_position_in_shares,
#                 diff_position_in_shares,
#             )
#             dfs.append(df_tmp)
#         hdbg.dassert(dfs, "Empty dataframe is empty.")
#         # Convert order to CSV.
#         df = pd.concat(dfs, axis=0)
#         order_txt = df.to_csv(index=False)
#         _LOG.debug("order_txt=\n%s", order_txt)
#         # Save as a file in the S3 location.
#         submitted_order_id = self._get_next_submitted_order_id()
#         s3_file_name = self._get_file_name(
#             wall_clock_timestamp,
#             submitted_order_id,
#             self._strategy_id,
#         )
#         # TODO(gp): Save the data in `log_dir`.
#         local_file_name = os.path.basename(s3_file_name)
#         hio.to_file(local_file_name, order_txt)
#         if not dry_run:
#             # TODO(gp): Make sure the file doesn't exist on S3.
#             # Copy the file to the S3 location.
#             # TODO(gp): Maybe save directly on S3.
#             # !aws s3 cp --profile "trading_sasm" \
#             #   --acl bucket-owner-full-control \
#             #   test.csv $file_name
#             # opts = '--profile "trading_sasm" --acl bucket-owner-full-control'
#             opts = "--acl bucket-owner-full-control"
#             cmd = f"aws s3 cp {opts} {local_file_name} {s3_file_name}"
#             hsystem.system(cmd)
#         else:
#             _LOG.info("Dry-run placing trades:\n%s", order_txt)
#         # TODO(gp): Check the `changed_count`, `unchanged_count`,
#         return s3_file_name
#
#     def _convert_order_to_df(
#         self,
#         curr_timestamp: pd.Timestamp,
#         asset_id: int,
#         curr_position_in_shares: int,
#         diff_position_in_shares: int,
#     ) -> pd.DataFrame:
#         # pylint: disable=line-too-long
#         """
#         :param asset_id: asset_id the target is for
#         :param curr_position_in_shares: the current position in shares)
#         :param diff_position_in_shares: the change in position in shares you wish
#             to enter
#         :return: the df should look like
#             ```
#             trade_date,asset_id,target_position,notional_limit,adjprice,adjprice_ccy,algo,STARTTIME,ENDTIME,MAXPCTVOL,
#             20211027,15151,7,26,12.5,USD,VWAP,10:19:38 EST,14:30:00 EST,3
#             ```
#         """
#         # pylint: enable=line-too-long
#         ig_order = collections.OrderedDict()
#         curr_timestamp = curr_timestamp.tz_convert("America/New_York")
#         # 20211116
#         trade_date = curr_timestamp.date()
#         ig_order["trade_date"] = trade_date.strftime("%Y%m%d")
#         ig_order["asset_id"] = asset_id
#         hdbg.dassert_isinstance(curr_position_in_shares, int)
#         ig_order["current_position"] = curr_position_in_shares
#         hdbg.dassert_isinstance(diff_position_in_shares, int)
#         ig_order["target_position"] = (
#             curr_position_in_shares + diff_position_in_shares
#         )
#         # Get the last price, using TWAP for robustness against `nan`.
#         bar_duration = "5T"
#         ts_col_name = "end_time"
#         asset_ids = [asset_id]
#         column = "close"
#         last_price = self.market_data.get_last_twap_price(
#             bar_duration, ts_col_name, asset_ids, column
#         )
#         hdbg.dassert_in(asset_id, last_price.index)
#         last_price = last_price[asset_id]
#         # TODO(gp): If there is still a `nan` we would like to try to
#         #  get an older price.
#         hdbg.dassert(
#             np.isfinite(last_price), "last_price=%s asset_id=%s", last_price, asset_id
#         )
#         hdbg.dassert_lte(0, last_price, "asset_id=%s", asset_id)
#         # - notional_limit
#         #   = max absolute notional allowed for an order that is sent
#         #     out to move you to the target position. If the order required to move
#         #     you to your target position exceeds this amount, then this target will
#         #     be rejected.
#         #   - E.g., target_position=7, current_position=5. Order qty would be 2.
#         #     Suppose adjprice = 12.5. Then order notional is 12.5 * 2 = $25.
#         #     If 25 > the notional_limit set here, the target is rejected.
#         # TODO(gp): Is abs needed?
#         notional_limit = last_price * abs(diff_position_in_shares) * (1 + 0.01)
#         ig_order["notional_limit"] = notional_limit
#         # - adjprice
#         #   = the latest price your system has seen for this asset_id.
#         #   - Used along notional_limit to perform the order notional check.
#         ig_order["adjprice"] = last_price
#         # - adjprice_ccy
#         #   = currency of last seen price. Always set to "USD" for US trading.
#         ig_order["adjprice_ccy"] = "USD"
#         # - algo
#         #   = name of broker algo that should be used for the order that will move
#         #   you to the desired target position.
#         ig_order["algo"] = "VWAP"
#         # The remaining columns are broker algo specific and will depend on what
#         # broker algo(s) you want to use.
#         # Examples for VWAP:
#         # - start_time
#         #   = Start time of VWAP algo order in format `HH:MM:SS ET`.
#         # - end_time
#         #   = End time of the VWAP algo order.
#         # - MAXPCTVOL
#         #   = Max participation rate (in %) of the VWAP algo order.
#         trade_start = curr_timestamp
#         ig_order["trade_start"] = trade_start.time().strftime("%H:%M:%S ET")
#         # TODO(gp): The duration of the order should be passed through a config.
#         # TODO(gp): The operation of computing start / end timestamp should be
#         #  factored out somehow in `Order`.
#         # TODO(gp): Add a check to make sure we don't place an order after the end
#         #  of the bar. This requires having knowledge of what bar we are currently
#         #  processing.
#         order_duration_in_mins = 5
#         freq = f"{order_duration_in_mins}T"
#         trade_end = curr_timestamp.ceil(freq)
#         ig_order["trade_end"] = trade_end.time().strftime("%H:%M:%S ET")
#         # TODO(gp): This is a percentage, right?
#         ig_order["MAXPCTVOL"] = 3
#         # Format as a series.
#         df = pd.DataFrame.from_dict(ig_order, orient="index").T
#         _LOG.debug("order_df=\n%s", hpandas.df_to_str(df))
#         return df
#
#     def _get_file_name(
#         self,
#         curr_timestamp: pd.Timestamp,
#         order_id: int,
#         strategy_id: str,
#         group_prefix: str = "spms",
#     ) -> str:
#         """
#         The file should look like:
#
#         s3://eglp-core-exch/files/spms/SAU1/cand/targets/YYYYMMDD000000/<filename>.csv
#         """
#         # The reference Java CF code looks like:
#         # String timestampStr = DateTime.now().toString("yyyyMMddHHmmssSSS");
#         # String.format("files/%s/%s/%s/targets/%s000000/%s_%s_%s.csv",
#         #       groupPrefix, strategyId, dropId, date.toString("yyyyMMdd"), s3FilePrefix,
#         #       date.toString("yyyyMMdd"), timestampStr);
#         dst_dir = f"s3://eglp-core-exch/files/{group_prefix}/{strategy_id}"
#         # Find the subdir to use place orders.
#         dir_name = self._get_S3_tradelist_path(
#             self._liveness, self._instance_type
#         )
#         dst_dir = os.path.join(dst_dir, dir_name, "targets")
#         # E.g., "targets/YYYYMMDD000000/<filename>.csv"
#         date_dir = curr_timestamp.strftime("%Y%m%d")
#         date_dir += "0" * 6
#         # Add a timestamp for readability.
#         curr_timestamp_as_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
#         file_name = f"sasm_positions.{order_id}.{curr_timestamp_as_str}.csv"
#         file_name = os.path.join(dst_dir, date_dir, file_name)
#         _LOG.debug("file_name=%s", file_name)
#         return file_name
#
#     def _get_fills(
#         self, as_of_timestamp: pd.Timestamp
#     ) -> List[oms.Fill]:  # pylint: disable=no-self-use
#         _ = as_of_timestamp
#         hdbg.dfatal("IG broker doesn't provide fills")
