import pandas as pd

import helpers.hunit_test as hunitest
import research_amp.transform as ramptran


class TestCalculateVwapTwap(hunitest.TestCase):
    """
    Test the calculation of VWAP and TWAP with different resampling rules.
    """

    def helper(self) -> pd.DataFrame:
        """
        Create data for testing.
        """
        timestamp_index = pd.date_range("2024-01-01", periods=10, freq="T")
        close = list(range(200, 210))
        volume = list(range(40, 50))
        asset_id = [11, 12] * 5
        data = {
            "timestamp": timestamp_index,
            "close": close,
            "volume": volume,
            "full_symbol": asset_id,
        }
        df = pd.DataFrame(data=data).set_index("timestamp")
        return df

    def test1(self) -> None:
        resample_rule = "5T"
        df = self.helper()
        result_df = ramptran.calculate_vwap_twap(df, resample_rule)
        # Define expected values.
        expected_length = 3
        expected_column_value = None
        expected_signature = r"""
        # df=
        index=[2024-01-01 00:00:00, 2024-01-01 00:10:00]
        columns=('close', 11),('close', 12),('twap', 11),('twap', 12),('volume', 11),('volume', 12),('vwap', 11),('vwap', 12)
        shape=(3, 8)
                                close            twap            volume            vwap
                                11        12        11        12        11        12        11            12
                  timestamp
        2024-01-01 00:00:00        200.0    NaN        200.0    NaN        40.0    NaN        200.000000    NaN
        2024-01-01 00:05:00        204.0    205.0    203.0    203.0    86.0    129.0    203.023256    203.062016
        2024-01-01 00:10:00        208.0    209.0    207.0    208.0    94.0    96.0    207.021277    208.020833
        """
        # Check signature.
        self.check_df_output(
            result_df,
            expected_length,
            expected_column_value,
            expected_column_value,
            expected_signature,
        )

    def test2(self) -> None:
        resample_rule = "1T"
        df = self.helper()
        result_df = ramptran.calculate_vwap_twap(df, resample_rule)
        # Define expected values.
        expected_length = 10
        expected_column_value = None
        expected_signature = r"""
        # df=
        index=[2024-01-01 00:00:00, 2024-01-01 00:09:00]
        columns=('close', 11),('close', 12),('twap', 11),('twap', 12),('volume', 11),('volume', 12),('vwap', 11),('vwap', 12)
        shape=(10, 8)
                            close            twap            volume            vwap
                            11        12        11        12        11        12        11        12
                  timestamp
        2024-01-01 00:00:00    200.0    NaN        200.0    NaN        40.0    NaN        200.0    NaN
        2024-01-01 00:01:00    NaN        201.0    NaN        201.0    NaN        41.0    NaN        201.0
        2024-01-01 00:02:00    202.0    NaN        202.0    NaN        42.0    NaN        202.0    NaN
        ...
                  timestamp
        2024-01-01 00:07:00    NaN        207.0    NaN        207.0    NaN        47.0    NaN        207.0
        2024-01-01 00:08:00    208.0    NaN        208.0    NaN        48.0    NaN        208.0    NaN
        2024-01-01 00:09:00    NaN        209.0    NaN        209.0    NaN        49.0    NaN        209.0
        """
        # Check signature.
        self.check_df_output(
            result_df,
            expected_length,
            expected_column_value,
            expected_column_value,
            expected_signature,
        )
