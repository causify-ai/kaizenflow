#!/bin/bash -xe
find . -name "install_jupyter_extensions.sh" | \grep -v docker_common | xargs -t -n 1 cp -v docker_common/install_jupyter_extensions.sh
