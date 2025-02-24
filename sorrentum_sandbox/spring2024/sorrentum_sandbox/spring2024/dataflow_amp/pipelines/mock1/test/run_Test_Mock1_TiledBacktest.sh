# pytest amp/dataflow_amp/system/mock1/test/test_mock1_tiledbacktest.py::Test_Mock1_NonTime_ForecastSystem_TiledBacktest::test1 -s --dbg --update_outcomes

if [[ 1 == 0 ]]; then
/app/dataflow/backtest/run_config_list.py \
    --experiment_builder dataflow.backtest.master_backtest.run_in_sample_tiled_backtest \
    --config_builder 'dataflow_amp.system.mock1.mock1_tile_config_builders.build_Mock1_tile_config_list("mock1_v1-top2.1T.2022-01-01_2022-02-01")' \
    --dst_dir /app/amp/dataflow_amp/system/mock1/test/outcomes/Test_Mock1_NonTime_ForecastSystem_TiledBacktest.test1/tmp.scratch/run_model \
    -v DEBUG --clean_dst_dir --no_confirm --num_threads serial
# --dry_run
fi;

#/app/amp/dataflow/backtest/run_config_stub.py --experiment_builder 'amp.dataflow.backtest.master_backtest.run_in_sample_tiled_backtest' --config_builder 'dataflow_amp.system.mock1.mock1_tile_config_builders.build_Mock1_tile_config_list("kibot_v1-top1.5T.2020-01-01_2020-03-01")' --config_idx 0 --dst_dir /app/amp/dataflow_amp/system/mock1/test/outcomes/Test_Mock1_NonTime_ForecastSystem_TiledBacktest.test1/tmp.scratch/run_model -v DEBUG

#/app/dataflow/backtest/run_config_stub.py --experiment_builder 'dataflow.backtest.master_backtest.run_in_sample_tiled_backtest' --config_builder 'dataflow_amp.system.mock1.mock1_tile_config_builders.build_Mock1_tile_config_list("mock1_v1-top2.1T.Jan2000")' --config_idx 0 --dst_dir /app/amp/dataflow_amp/system/mock1/test/outcomes/Test_Mock1_NonTime_ForecastSystem_TiledBacktest.test1/tmp.scratch/run_model -v INFO 2>&1 | tee log.txt
