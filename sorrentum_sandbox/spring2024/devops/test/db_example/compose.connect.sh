# Connect to the DB.
network_name="main_network"
docker \
  run \
  --rm \
  -ti \
  --network $network_name \
  -e PGPASSWORD=topsecret \
  postgres:13 \
  psql -h test_postgres -U postgres

# network_name="main_network" docker run --rm -ti --network $network_name -e PGPASSWORD=topsecret postgres:13 psql -h db_example_oms_postgres2344_1 -U aljsdalsd
