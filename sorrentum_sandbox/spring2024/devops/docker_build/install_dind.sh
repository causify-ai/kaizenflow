#!/usr/bin/env bash
#
# Install Docker-in-Docker.
#

# From https://www.digitalocean.com/community/tutorials/how-to-install-and-use-docker-on-ubuntu-18-04

set -ex

FILE_NAME="devops/docker_build/install_dind.sh"
echo "#############################################################################"
echo "##> $FILE_NAME"
echo "#############################################################################"

# Install the latest version of Docker.
# `https://docs.docker.com/engine/install/ubuntu/`.
sudo apt-get -y update
sudo apt-get -y install ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch="$(dpkg --print-architecture)" signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  "$(. /etc/os-release && echo "$VERSION_CODENAME")" stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get -y update
sudo apt-get -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Install the latest version of `docker-compose`, see
# `https://docs.docker.com/compose/install/`.
# Extract version from JSON output, e.g., `"name": "v2.3.3"` -> "v2.3.3". We
# could use `jq` to extract data from JSON but this would imply introducing
# another dependency.
COMPOSE_LATEST_VERSION=$(curl https://api.github.com/repos/docker/compose/releases/latest | grep '\"tag_name\":' | sed -E 's/.*\"([^\"]+)\".*/\1/')
COMPOSE_BINARY="/usr/local/bin/docker-compose"
curl -SL https://github.com/docker/compose/releases/download/$COMPOSE_LATEST_VERSION/docker-compose-$(uname -s)-$(uname -m) -o $COMPOSE_BINARY
# Apply executable permissions to the binary.
chmod +x $COMPOSE_BINARY
# Check version.
COMPOSE_VERSION=$(docker-compose --version)
echo "docker-compose --version: $COMPOSE_VERSION"
