#!/usr/bin/env bash

set -e

export PYTHONPATH=$PYTHONPATH:/app

# Create configurations for controller.
CMD="python /app/scripts/make_ib_controller_init_file.py \
     --user ${TWSUSERID} \
     --password ${TWSPASSWORD} \
     --stage ${STAGE}"
echo "> $CMD"
eval $CMD

CMD="python /app/scripts/make_jts_init_file.py \
    --trusted_ips 127.0.0.1,${TRUSTED_IPS}"
echo "> $CMD"
eval $CMD

# Run controller.
xvfb-daemon-run /opt/IBController/Scripts/DisplayBannerAndLaunch.sh &

# Tail latest in log dir.
sleep 1
tail -f $(find $LOG_PATH -maxdepth 1 -type f -printf "%T@ %p\n" | sort -n | tail -n 1 | cut -d' ' -f 2-) &

# Give enough time for a connection before trying to expose on 0.0.0.0:$(API_PORT)
# TODO(gp): Is this needed?
echo "Waiting 30 secs for TWS to come up before exposing the ports"
sleep 30
echo "Forking port..."
socat TCP-LISTEN:${IB_API_PORT},fork TCP:127.0.0.1:4001
echo "Ready"
