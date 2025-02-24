# Create a DB in a container called test_postgres.
#network_name="compose_default"
network_name="main_network"
docker \
  run \
  --rm \
  -ti \
  --network $network_name \
  -e POSTGRES_PASSWORD=topsecret \
  --name db_example_oms_postgres2344_2 \
  postgres:13
