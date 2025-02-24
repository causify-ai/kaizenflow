import logging
import os
from typing import Any, Dict, List

import pytest

import helpers.hdbg as hdbg
import helpers.hio as hio
import helpers.hs3 as hs3
import helpers.hunit_test as hunitest
import oms.broker.broker_example as obrbrexa
import oms.broker.ccxt.ccxt_logger as obcccclo
import oms.fill as omfill
import oms.order.order as oordorde

_LOG = logging.getLogger(__name__)


class TestReplayedFillsDataFrameBroker(hunitest.TestCase):
    @pytest.mark.slow("11 seconds.")
    def test1(self) -> None:
        """
        Verify if ReplayFillsDataFrameBroker return the logged OMS fills in
        correct order.
        """
        # Load data from s3.
        use_only_test_class = True
        s3_input_dir = self.get_s3_input_dir(
            use_only_test_class=use_only_test_class
        )
        scratch_dir = self.get_scratch_space()
        aws_profile = "ck"
        hs3.copy_data_from_s3_to_local_dir(s3_input_dir, scratch_dir, aws_profile)
        # Initialize logger.
        log_dir = os.path.join(scratch_dir, "log")
        # TODO(Grisha): remove dependency from `oms.broker.ccxt.ccxt_logger`
        # and generate fills on the fly.
        logger = obcccclo.CcxtLogger(log_dir, mode="read")
        oms_fills_file_paths = logger._get_files(logger._oms_fills_dir)
        oms_parent_orders_file_paths = logger._get_files(
            logger._oms_parent_orders_dir, file_extension="json"
        )
        # Oms fills and OMS orders should have equal number of file paths.
        hdbg.dassert_eq(
            len(oms_fills_file_paths), len(oms_parent_orders_file_paths)
        )
        # Read OMS fills and OMS parent orders from logs.
        oms_fills = self._read_oms_json_log_files(
            oms_fills_file_paths, oms_parent_orders_file_paths
        )
        # Intitialize replayed fill broker.
        event_loop = None
        broker = obrbrexa.get_ReplayedFillsDataFrameBroker_example1(
            oms_fills, event_loop
        )
        # Current test case have 2 OMS fills verify both.
        # Verify the first OMS fill is as expected.
        actual = broker.get_fills()
        expected = oms_fills[0]
        self.assert_equal(str(actual), str(expected))
        # Verify the second OMS fill is as expected.
        actual = broker.get_fills()
        expected = oms_fills[1]
        self.assert_equal(str(actual), str(expected))
        # Verify empty OMS fills.
        with self.assertRaises(StopIteration):
            _ = broker.get_fills()

    def _read_oms_json_log_files(
        self,
        oms_fills_file_paths: List[str],
        oms_parent_orders_file_paths: List[str],
    ) -> List[List[omfill.Fill]]:
        """
        Read the logged data of OMS fills and OMS parent orders from JSON.
        """
        oms_fills = []
        for order_path, fill_path in zip(
            oms_parent_orders_file_paths, oms_fills_file_paths
        ):
            order_data = hio.from_json(order_path, use_types=True)
            fill_data = hio.from_json(fill_path, use_types=True)
            fill_objects = self._create_oms_fills_object(fill_data, order_data)
            oms_fills.append(fill_objects)
        return oms_fills

    def _create_oms_fills_object(
        self,
        fills: List[Dict[str, Any]],
        orders: List[Dict[str, Any]],
    ) -> List[omfill.Fill]:
        """
        Create list of OMS fills object from logged OMS fills and OMS parent
        orders data.
        """
        oms_fills = []
        for fill_data, order_data in zip(fills, orders):
            order = oordorde.Order(
                order_data["creation_timestamp"],
                order_data["asset_id"],
                order_data["type_"],
                order_data["start_timestamp"],
                order_data["end_timestamp"],
                order_data["curr_num_shares"],
                order_data["diff_num_shares"],
                order_id=order_data["order_id"],
                extra_params=order_data["extra_params"],
            )
            fill = omfill.Fill(
                order,
                fill_data["timestamp"],
                fill_data["num_shares"],
                fill_data["price"],
            )
            oms_fills.append(fill)
        return oms_fills
