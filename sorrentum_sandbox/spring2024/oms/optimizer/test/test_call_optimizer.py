import logging

import pandas as pd
import pytest

import core.config as cconfig
import helpers.hpandas as hpandas
import helpers.hunit_test as hunitest
import oms.optimizer.call_optimizer as oopcaopt

_LOG = logging.getLogger(__name__)


@pytest.mark.skip("Cannot update the goldens, see CmTask1357.")
class TestOptimize(hunitest.TestCase):
    @staticmethod
    def get_prediction_df() -> pd.DataFrame:
        """
        Get prediction data.
        """
        df = pd.DataFrame(
            [[1, 1000, 0.05, 0.05], [2, 1500, 0.09, 0.07], [3, -500, 0.03, 0.08]],
            range(0, 3),
            ["asset_id", "position", "prediction", "volatility"],
        )
        return df

    @staticmethod
    def helper(
        config: cconfig.Config,
        df: pd.DataFrame,
        tmp_dir: str,
    ) -> str:
        """
        Run the optimizer and covert output to string.
        """
        actual = oopcaopt.run_optimizer(config, df, tmp_dir=tmp_dir)
        precision = 5
        actual_str = hpandas.df_to_str(actual, precision=precision)
        return actual_str

    def test_only_gmv_constraint(self) -> None:
        """
        Same test as Test_SinglePeriodOptimizer1.test_only_gmv_constraint() but
        using the remote execution.
        """
        dict_ = {
            "volatility_penalty": 0.0,
            "dollar_neutrality_penalty": 0.0,
            "turnover_penalty": 0.0,
            "target_gmv": 3000,
            "target_gmv_upper_bound_multiple": 1.00,
        }
        config = cconfig.Config.from_dict(dict_)
        df = self.get_prediction_df()
        scratch_dir = self.get_scratch_space()
        actual = self.helper(config, df, scratch_dir)
        expected = r"""
                  target_positions  target_notional_trades  target_weights  target_weight_diffs
        asset_id
        1                 -3.71100             -1003.71100        -0.00124             -0.33457
        2               2962.92836              1462.92836         0.98764              0.48764
        3                 -3.71100               496.28900        -0.00124              0.16543
        """
        self.assert_equal(actual, expected, fuzzy_match=True)
