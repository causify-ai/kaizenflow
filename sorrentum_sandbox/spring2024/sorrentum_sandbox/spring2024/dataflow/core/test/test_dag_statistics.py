import logging
import os

import pandas as pd

import dataflow.core.dag_statistics as dtfcodasta
import helpers.hparquet as hparque
import helpers.hunit_test as hunitest

_LOG = logging.getLogger(__name__)


class Test_get_dag_node_names(hunitest.TestCase):
    def test1(self) -> None:
        """
        Test that DAG node names are extracted and sorted correctly.
        """
        test_dir = self.get_scratch_space()
        # Create a dummy DataFrame as a placeholder.
        df = pd.DataFrame()
        # Set node names to build test files for.
        node_names = [
            "read_data",
            "generate_feature_panels",
            "resample",
            "compute_vol",
            "normalize_feature_panels",
            "sqrt",
            "compress",
            "xs_adj",
            "compress_adj",
            "generate_feature",
            "process_forecasts",
        ]
        # Set common tail for all DAG node file names.
        file_name_tail = "df_out.20230101_080000.20230101_080033.parquet"
        # Generate DAG node Parquet files and put them to the test dir.
        for order, name in enumerate(node_names):
            file_name = f"predict.{order}.{name}.{file_name_tail}"
            file_path = os.path.join(test_dir, file_name)
            hparque.to_parquet(df, file_path)
        # Extract DAG node names from parquet file names.
        actual = dtfcodasta.get_dag_node_names(test_dir)
        # Check.
        # TODO(Dan): Consider changing expected format and use `fuzzy_match` switch.
        expected = (
            r"['predict.0.read_data', "
            r"'predict.1.generate_feature_panels', "
            r"'predict.2.resample', "
            r"'predict.3.compute_vol', "
            r"'predict.4.normalize_feature_panels', "
            r"'predict.5.sqrt', "
            r"'predict.6.compress', "
            r"'predict.7.xs_adj', "
            r"'predict.8.compress_adj', "
            r"'predict.9.generate_feature', "
            r"'predict.10.process_forecasts']"
        )
        self.assert_equal(str(actual), expected)


class Test_compare_dag_outputs(hunitest.TestCase):
    """
    Test that `compare_dag_outputs()` works correctly.
    """

    def test1(self) -> None:
        """
        Test that function does not raise an assertion when at least one of the
        paths doesn't exist.
        """
        # Define DAG paths where at least one of the path doesn't exist.
        scratch_dir = self.get_scratch_space()
        dag_path_dict = {
            # Test class creates it when the corresponding method is called.
            "prod": scratch_dir,
            # This dir doesn't exist.
            "sim": os.path.join(scratch_dir, "sim"),
        }
        node_name = "predict.10.process_forecasts"
        bar_timestamp = "2024-01-26 08:36:00-05:00"
        # Call the function.
        actual = str(
            dtfcodasta.compare_dag_outputs(
                dag_path_dict, node_name, bar_timestamp
            )
        )
        # Check. It should exit from the function safely, i.e. return `None`.
        expected = "None"
        self.assert_equal(actual, expected)
