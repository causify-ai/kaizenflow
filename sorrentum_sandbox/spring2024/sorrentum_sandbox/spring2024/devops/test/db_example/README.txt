# Start / connect to DB using Docker command lines

- Start a DB using Docker command line:
  ```
  > sudo docker \
    run \
    --rm \
    -ti \
    --network compose_default \
    -e POSTGRES_PASSWORD=topsecret \
    --name test_postgres postgres:13
  ```

- Connect to the DB using Docker command line:
  ```
  > sudo docker \
    run \
    --rm \
    -ti \
    --network compose_default \
    -e PGPASSWORD=topsecret \
    postgres:13 \
    psql -h test_postgres -U postgres
  ```

- Connect to the DB from inside Docker container:
  ```
  > i docker_bash
  docker> PGPASSWORD=topsecret psql -h test_postgres -U postgres
  ```

# Docker compose for DB and command line to connect

- Start a DB using Docker compose:
  ```
  > DOCKER_DIR=amp/devops/test/db_example
  > docker-compose --file $DOCKER_DIR/docker-compose_2344.yml --env-file $DOCKER_DIR/local.oms_db_config_2344.env up -d oms_postgres2344
  ```

- Connect to the DB from inside Docker container should work both using the
  container name and referring to `localhost`
  ```
  > i docker_bash
  docker> psql --host=oms_postgres2344 --port=2344 --user aljsdalsd -d oms_postgres_db_local
    Should not work since by specifying the port we get out of the Docker host
    network
  docker> psql --host=localhost --port=7776 --user aljsdalsd -d oms_postgres_db_local
  docker> psql --host=gpmac --port=7776 --user aljsdalsd -d oms_postgres_db_local
  ```

- Connect from outside the Docker container
  ```
  > psql --host=localhost --port=7776 --user aljsdalsd -d oms_postgres_db_local
  ```

# Remarks
1) one can use `telnet` to check if a port is open instead of `psql`

2) If server and client are both running inside a container, one doesn't need the
  port but can just the service name
  - The ports in YAML is only for accesing the container from outside the host
    network

- When using Docker command line the name from `docker container ls` is the name
  that can be used to resolve the service name

- When using `compose` the name in `docker container ls` doesn't match the name
  that one needs to use to resolve the service. E.g.,

  ```
  > docker container ls | grep post
  52866e458788        postgres:13
  "docker-entrypoint.s…"   2 minutes ago       Up 2 minutes        5432/tcp db_example_oms_postgres2344_1
  ```

- One needs to use `oms_postgres2344` and `db_example_oms_postgres2344_1`

3) The two different modes are `host` and `bridge`

- The default is bridge: each container gets its own network stack

4) Use `docker inspect 26cbffa5673d` to look at the container connectivity

# Refs
- https://docs.docker.com/network/
- https://docs.docker.com/network/bridge/
- https://github.com/dnvriend/docker-networking-test
