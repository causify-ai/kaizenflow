# import logging
# from typing import Any
#
# import helpers.hunit_test as hunitest
# import im_v2.ig.ig_utils as imvigigut
# import vendors_lime.datastream_liquidity.utils as vldaliut
#
# _LOG = logging.getLogger(__name__)
#
#
# class TestDatastreamLiquidityUtils1(hunitest.TestCase):
#    def test_get_liquidity_data1(self) -> None:
#        """
#        Get data for one day and multiple assets.
#        """
#        # SPY: 10971
#        # AAPL: 17085
#        # BAC: 15224
#        asset_ids = [10971, 17085, 15224]
#        dates = ["2021-06-17"]
#        dates = list(map(imvigigut.convert_to_date, dates))
#        self._get_liquidity_data_helper(asset_ids, dates)
#
#    def test_get_liquidity_data2(self) -> None:
#        """
#        Get data for multiple days.
#        """
#        asset_ids = [17085, 15224]
#        dates = ["2021-06-17", "2021-06-18"]
#        dates = list(map(imvigigut.convert_to_date, dates))
#        self._get_liquidity_data_helper(asset_ids, dates)
#
#    def _get_liquidity_data_helper(self, *args: Any, **kwargs: Any) -> None:
#        asset_ids = args[0]
#        _LOG.debug("%s", asset_ids)
#        #
#        df = vldaliut.get_liquidity_data(*args, **kwargs)
#        #
#        df_as_str = hpandas.df_to_str(df.T, num_rows=None)
#        # TODO(Paul): Add summary stats to test.
#        actual = []
#        actual_tmp = "## transposed df_as_str=\n%s" % df_as_str
#        _LOG.debug("%s", actual_tmp)
#        actual.append(actual_tmp)
#        actual_result = "\n".join(actual)
#        self.check_string(actual_result)
