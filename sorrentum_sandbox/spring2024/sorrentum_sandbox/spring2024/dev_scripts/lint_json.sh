#!/bin/bash

# Lint a Python pretty-print / JSON data, e.g.,
# ```
# {
#     'bid_ask_lookback': '60S',
#     'child_order_quantity_computer': {'object_type': 'StaticSchedulingChildOrderQuantityComputer'},
#     'limit_price_computer': {
#         'max_deviation': 0.01,
#         'object_type': 'LimitPriceComputerUsingSpread',
#                             'passivity_factor': 0.55},
# 'log_dir': '/app/system_log_dir',
# 'raw_data_reader_signature': 'realtime.airflow.downloaded_200ms.postgres.bid_ask.futures.v7.ccxt.binance.v1_0_0',
# 'secret_identifier': 'binance.preprod.trading.4',
# 'stage': 'preprod',
# 'universe_version': 'v7.4'}
# ```

# Lint the clipboard:
# ```
# > pbpaste | lint_json.sh
# ```
#
# Lint a file in place
# ```
# lint_json.sh file
# ```

# Load data.
if [ $# -eq 0 ]; then
    # No arguments provided, read from stdin.
    input=$(cat)
    from_stdin=1
elif [ -f "$1" ]; then
    # Argument is a file, read from the file.
    echo "Reading from $1"
    input=$(cat "$1")
    from_stdin=0
else
    echo "File '$1' not found."
    exit 1
fi
#echo $input

# Process data.
TEMP="/tmp/temp"
echo $input >$TEMP
perl -i -pe 's/'\''/"/g' $TEMP
python -m json.tool ${TEMP} > ${TEMP}2

# Save data.
if [[ $from_stdin == 1 ]]; then
    cat ${TEMP}2
else
    cat ${TEMP}2 >$1
    echo "Saved result into $1"
fi;
