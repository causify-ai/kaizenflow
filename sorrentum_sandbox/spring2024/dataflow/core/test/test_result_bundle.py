import logging
import os

import pandas as pd

import core.config as cconfig
import dataflow.core.result_bundle as dtfcorebun
import dataflow.core.utils as dtfcorutil
import helpers.hprint as hprint
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


def _get_init_config() -> cconfig.Config:
    df = pd.DataFrame([range(5)], columns=[f"col{i}" for i in range(5)])
    config_ = {"key": "val"}
    info_ = {"df_info": dtfcorutil.get_df_info_as_string(df)}
    column_to_tags_dict = {
        "col0": ["feature_col"],
        "col1": ["target_col", "step_0"],
        "col2": ["target_col", "step_1"],
        "col3": ["prediction_col", "step_0"],
        "col4": ["prediction_col", "step_1"],
    }
    init_dict = {
        "config": config_,
        "result_nid": "leaf_node",
        "method": "fit",
        "result_df": df,
        "column_to_tags": column_to_tags_dict,
        "info": info_,
        "payload": None,
    }
    init_config = cconfig.Config.from_dict(init_dict)
    return init_config


class TestResultBundle(hunitest.TestCase):
    def test_to_config1(self) -> None:
        """
        Convert a `ResultBundle` to a config.
        """
        rb = self._get_result_bundle()
        # Check.
        actual_config = rb.to_config(commit_hash=False)
        txt = f"config without 'commit_hash' field:\n{actual_config}"
        self.check_string(txt)

    def test_from_config1(self) -> None:
        """
        Initialize a `ResultBundle` from a config.
        """
        # Initialize a `ResultBundle` from a config.
        init_config = _get_init_config()
        rb = dtfcorebun.ResultBundle.from_config(init_config)
        # Check.
        actual_config = rb.to_config(commit_hash=False)
        txt = f"config without 'commit_hash' field:\n{actual_config}"
        self.check_string(txt)

    def test_to_dict_and_back(self) -> None:
        """
        Round-trip conversion using `from_config()` and `to_config()`.
        """
        # Initialize a `ResultBundle` from a config.
        init_config = _get_init_config()
        result_bundle = dtfcorebun.ResultBundle.from_config(init_config)
        # This pattern is used in `master_backtest.py` before pickling.
        rb_as_dict = result_bundle.to_config().to_dict()
        # After unpickling, we convert to a `Config`, then to a `ResultBundle`.
        result_bundle_2 = dtfcorebun.ResultBundle.from_config(
            cconfig.Config.from_dict(rb_as_dict)
        )
        # Check.
        self.assert_equal(str(result_bundle), str(result_bundle_2))

    def test_pickle1(self) -> None:
        rb = self._get_result_bundle()
        # Serialize.
        dir_name = self.get_scratch_space()
        file_name = os.path.join(dir_name, "result_bundle.pkl")
        rb.to_pickle(file_name, use_pq=False)
        # Compute the signature of the dir.
        actual = hunitest.get_dir_signature(dir_name, include_file_content=False)
        # Check.
        expected = """
        # Dir structure
        $GIT_ROOT/dataflow/core/test/outcomes/TestResultBundle.test_pickle1/tmp.scratch
        $GIT_ROOT/dataflow/core/test/outcomes/TestResultBundle.test_pickle1/tmp.scratch/result_bundle.v1_0.pkl
        """
        expected = hprint.dedent(expected)
        self.assert_equal(str(actual), str(expected), purify_text=True)

    def test_get_tags_for_column1(self) -> None:
        rb = self._get_result_bundle()
        #
        actual = rb.get_tags_for_column("col2")
        expected = ["target_col", "step_1"]
        self.assert_equal(str(actual), str(expected))

    def test_get_columns_for_tag1(self) -> None:
        rb = self._get_result_bundle()
        #
        actual = rb.get_columns_for_tag("step_1")
        expected = ["col2", "col4"]
        self.assert_equal(str(actual), str(expected))

    def _get_result_bundle(self) -> dtfcorebun.ResultBundle:
        """
        Initialize a `ResultBundle` from a config.
        """
        init_config = _get_init_config()
        rb = dtfcorebun.ResultBundle.from_config(init_config)
        return rb


# #############################################################################


class TestPredictionResultBundle(hunitest.TestCase):
    def test_to_config1(self) -> None:
        init_config = _get_init_config()
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        actual_config = prb.to_config(commit_hash=False)
        self.check_string(f"config without 'commit_hash' field:\n{actual_config}")

    def test_feature_col_names1(self) -> None:
        init_config = _get_init_config()
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        actual = prb.feature_col_names
        expected = ["col0"]
        self.assertListEqual(actual, expected)

    def test_target_col_names1(self) -> None:
        init_config = _get_init_config()
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        actual = prb.target_col_names
        expected = ["col1", "col2"]
        self.assertListEqual(actual, expected)

    def test_prediction_col_names1(self) -> None:
        init_config = _get_init_config()
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        actual = prb.prediction_col_names
        expected = ["col3", "col4"]
        self.assertListEqual(actual, expected)

    def test_get_target_and_prediction_col_names_for_tags1(self) -> None:
        init_config = _get_init_config()
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        actual = prb.get_target_and_prediction_col_names_for_tags(
            tags=["step_0", "step_1"]
        )
        expected = {"step_0": ("col1", "col3"), "step_1": ("col2", "col4")}
        self.assertDictEqual(actual, expected)

    def test_get_target_and_prediction_col_names_for_tags2(self) -> None:
        """
        Try to extract columns with no target column for given tag.
        """
        init_config = _get_init_config()
        init_config["column_to_tags"].pop("col1")
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        with self.assertRaises(AssertionError):
            prb.get_target_and_prediction_col_names_for_tags(tags=["step_0"])

    def test_get_target_and_prediction_col_names_for_tags3(self) -> None:
        """
        Extract columns with no target column for another tag.
        """
        init_config = _get_init_config()
        init_config["column_to_tags"].pop("col1")
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        actual = prb.get_target_and_prediction_col_names_for_tags(tags=["step_1"])
        expected = {"step_1": ("col2", "col4")}
        self.assertDictEqual(actual, expected)

    def test_get_targets_and_predictions_for_tags1(self) -> None:
        init_config = _get_init_config()
        prb = dtfcorebun.PredictionResultBundle(**init_config)
        actual = prb.get_targets_and_predictions_for_tags(
            tags=["step_0", "step_1"]
        )
        expected = {
            "step_0": (pd.Series([1], name="col1"), pd.Series([3], name="col3")),
            "step_1": (pd.Series([2], name="col2"), pd.Series([4], name="col4")),
        }
        # Compare dicts.
        self.assertListEqual(list(actual.keys()), list(expected.keys()))
        for tag, (target, prediction) in actual.items():
            pd.testing.assert_series_equal(target, expected[tag][0])
            pd.testing.assert_series_equal(prediction, expected[tag][1])
