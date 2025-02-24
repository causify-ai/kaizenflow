#!/bin/bash -xe

replace_text.py \
    --old "_get_docker_cmd" \
    --new "_get_docker_run_cmd" 
