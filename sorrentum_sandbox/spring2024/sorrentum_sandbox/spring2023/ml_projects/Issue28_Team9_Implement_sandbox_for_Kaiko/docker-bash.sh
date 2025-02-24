
if [ $# -ne 1 ]
then
    container_id=$(docker ps -aqf "name=kaiko")
else
    container_id=$(docker ps -aqf "name=$1")
fi


if [ -z "$container_id" ]
then
    echo "Error: Container '$1' not found"
    exit 1
fi

docker exec -it $container_id /bin/bash
