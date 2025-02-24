#!/bin/bash -xe

clear

AMP_DIR="./amp"
#AMP_DIR="."

if [[ -z $AMP_DIR ]]; then
    echo "Can't find AMP_DIR=$AMP_DIR"
    exit -1
fi;

# Install the profiling tools, if needed.
# $AMP_DIR/devops/docker_build/install_cprofile.sh

# Exec.
cmd_line="${AMP_DIR}/oms/order_processing/run_process_forecasts.py --backtest_file_name /cache/tiled_simulations/rc_experiment.RH8Ed.eg_v2_0-all.5T.2012_2022.run1/tiled_results --asset_id_col egid --log_dir process_forecasts_backtest"

# Delete all the profiling info.
# ls -1 prof.*.bin prof.*.lprof
# rm -rf prof.*.bin prof.*.lprof

tag=3iters.v1

# Base run.
if [[ 1 == 1 ]]; then
    time $cmd_line
fi;

# cProfile.
if [[ 1 == 0 ]]; then
    # Profile.
    PROF_FILE=prof.${tag}.bin
    LOG_FILE=log.${tag}.txt

    python -m cProfile -o $PROF_FILE $cmd_line 2>&1 | tee $LOG_FILE

    # Post-process.
    ${AMP_DIR}/dev_scripts/process_prof.py --file_name $PROF_FILE
fi;

# Line profile.
if [[ 1 == 0 ]]; then
    # Profile.
    kernprof -o prof.$tag.lprof -l $cmd_line

    # Post-process.
    python -m line_profiler prof.$tag.lprof
fi;
