# //amp/im/ib/connect/tasks.py

import logging
import os

from invoke import task
from lib_tasks import STAGE, get_image, set_default_params

import helpers.hdbg as dbg

# We inline the code here since we need to make it visible to `invoke`, although
# `from ... import *` is bad practice.
# from lib_tasks import *


_LOG = logging.getLogger(__name__)

# #############################################################################
# Setup.
# #############################################################################

AM_ECR_BASE_PATH = os.environ["AM_ECR_BASE_PATH"]


default_params = {
    "AM_ECR_BASE_PATH": ECR_BASE_PATH,
    # When testing a change to the build system in a branch you can use a different
    # image, e.g., `XYZ_tmp` to not interfere with the prod system.
    # "BASE_IMAGE": "..._tmp",
    "BASE_IMAGE": "im_tws",
    "DEV_TOOLS_IMAGE_PROD": f"{AM_ECR_BASE_PATH}/dev_tools:prod",
}


set_default_params(default_params)

# i docker_build_local_image
# i im_tws_start_ib_interface --stage local --ib-app="TWS"


@task
def im_tws_start_ib_interface(ctx, stage=STAGE, ib_app=""):
    dbg.dassert_in(ib_app, ("TWS", "GATEWAY"))
    base_image = ""
    # ****.dkr.ecr.us-east-1.amazonaws.com/im_tws:dev
    image = get_image(base_image, stage)
    # TODO(gp): Use `curl ifconfig.me` to get host's IP.
    trusted_ips = ""
    vnc_password = "12345"
    vnc_port = 5901
    ib_api_port = 4001
    print(ib_api_port)
    # ib_api_port = 4001
    # TODO(gp): Rename API_PORT -> IB_API_PORT
    # TODO(gp): Where is IB_APP defined?
    cmd = rf"""
    TWSUSERID="gpsagg314" \
    TWSPASSWORD="test" \
    IB_APP={ib_app} \
    IMAGE="{image}" \
    TRUSTED_IPS={trusted_ips} \
    VNC_PORT={vnc_port} \
    VNC_PASSWORD={vnc_password} \
    IB_API_PORT={ib_api_port} \
    docker-compose \
        -f devops/compose/docker-compose.local.yml \
        run --rm \
        -l user=$USER \
        -l app="ib_connect" \
        --service-ports \
        tws \
        /bin/bash
    """
    ctx.run(cmd)
