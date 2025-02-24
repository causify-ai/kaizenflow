#!/usr/bin/env bash

# This needs to be kept in sync with devops/docker_build/etc_sudoers.
# TODO(gp): Find a solution where you don't have to specify all the potential
# users up front.
# The problem is that `/etc/sudoers` needs to be ready before the entrypoint is
# executed. On the other side we get to know the user ID when the entrypoint
# is executed. Thus we can't easily use a script to generate this script and
# `etc_sudoers` but we need to do it when the Docker container is created.
OPTS="--home-dir /home"

# Mac user.
useradd -u 501 $OPTS user_501
usermod -aG docker user_501

# Linux users.
# We start from id=1000 because IDs below 1000 are usually reserved for system
# users and groups, the upper bound can be changed if needed.
for current_linux_id in {1000..1050}
do
  useradd -u $current_linux_id $OPTS user_$current_linux_id
  usermod -aG docker user_$current_linux_id
done

sudo chmod -R 777 /home

# Allow users to access /mnt/tmpfs.
# TODO(gp): We could change the permissions in fstab.
sudo chmod 777 /mnt
