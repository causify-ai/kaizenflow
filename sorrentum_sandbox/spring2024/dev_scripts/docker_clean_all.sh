#!/bin/bash -xe

# From https://stackoverflow.com/questions/34658836/docker-is-in-volume-in-use-but-there-arent-any-docker-containers

docker stop $(docker ps -aq)
docker rm $(docker ps -aq)
docker network prune -f
#docker rmi -f $(docker images --filter dangling=true -qa)
docker volume rm $(docker volume ls --filter dangling=true -q)
#docker rmi -f $(docker images -qa)
