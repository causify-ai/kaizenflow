import helpers.hunit_test as hunitest
import im_v2.common.universe.universe_utils as imvcuunut


class TestStringToNumericalId(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test that string id is converted to numerical correctly.
        """
        num_id = imvcuunut.string_to_numerical_id("binance::BTC_USDT")
        self.assertEqual(num_id, 1467591036)


class TestBuildNumericalToStringIdMapping(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test that numerical to string ids mapping is being built correctly.
        """
        mapping = imvcuunut.build_numerical_to_string_id_mapping(
            ["gateio::XRP_USDT", "kucoin::SOL_USDT"]
        )
        self.assertEqual(len(mapping), 2)
        self.assert_equal(mapping[2002879833], "gateio::XRP_USDT")
        self.assert_equal(mapping[2568064341], "kucoin::SOL_USDT")
