import os
import unittest.mock as umock

import pytest
from invoke import MockContext, Result

import core.config as cconfig
import dev_scripts.lib_tasks_run_model_experiment_notebooks as dsltrmeno
import helpers.hpickle as hpickle
import helpers.hunit_test as hunitest


class Test_run_notebooks(hunitest.TestCase):
    # Mock call to run and publish notebook functions.
    mock__run_notebook = umock.patch.object(dsltrmeno, "_run_notebook")
    mock_publish_notebook = umock.patch.object(
        dsltrmeno, "publish_system_reconciliation_notebook"
    )
    mock__publish_trading_notebook = umock.patch.object(
        dsltrmeno, "_publish_master_trading_notebook"
    )
    # Mocking context object.
    ctx = MockContext(Result("success"))

    # This will be run before and after each test.
    @pytest.fixture(autouse=True)
    def setup_teardown_test(self):
        # Run before each test.
        self.set_up_test()
        yield
        # Run after each test.
        self.tear_down_test()

    def set_up_test(self) -> None:
        # Create new mocks from patch's start() method.
        self.run__notebook_mock: umock.MagicMock = self.mock__run_notebook.start()
        self.run__notebook_mock.return_value = None
        self.publish_notebook_mock: umock.MagicMock = (
            self.mock_publish_notebook.start()
        )
        self.publish_notebook_mock.return_value = None
        self.publish_notebook_trading_mock = (
            self.mock__publish_trading_notebook.start()
        )
        self.publish_notebook_trading_mock.return_value = None

    def tear_down_test(self) -> None:
        self.mock__run_notebook.stop()
        self.mock_publish_notebook.stop()
        self.mock__publish_trading_notebook.stop()

    def test1(self) -> None:
        """
        Check if the function correctly handles a broker only run.".
        """
        # Prepare mock data.
        scratch_space = self.get_scratch_space()
        broker_only_config = {
            "parent_order_duration_in_min": 32,
            "universe": "v8",
            "child_order_execution_freq": "hourly",
        }
        file_name = os.path.join(scratch_space, "args.json")
        hpickle.to_json(file_name, broker_only_config)
        # Run test.
        dsltrmeno.run_notebooks(
            self.ctx,
            system_log_dir=scratch_space,
            base_dst_dir="/notebooks_output",
        )

    def test2(self) -> None:
        """
        Check if the function correctly handles a full system run.".
        """
        # Prepare mock data.
        full_cfg_path = self.get_scratch_space()
        full_system_config = {
            "dag_runner_config": {
                "bar_duration_in_secs": 1800,
            },
            "market_data_config": {
                "universe_version": "v8",
                "im_client_config": {
                    "table_name": "ABC",
                },
            },
            "process_forecasts_node_dict": {
                "process_forecasts_dict": {
                    "order_config": {
                        "execution_frequency": "hourly",
                    }
                }
            },
            "portfolio_config": {"mark_to_market_col": "40"},
        }
        cfg_path, _ = os.path.split(full_cfg_path)
        file_name = os.path.join(
            cfg_path, "system_config.output.values_as_strings.pkl"
        )
        config = cconfig.Config.from_dict(full_system_config)
        hpickle.to_pickle(config, file_name)
        # Run test.
        dsltrmeno.run_notebooks(
            self.ctx,
            system_log_dir=full_cfg_path,
            base_dst_dir="/notebooks_output",
        )
