"""
Import as:

import oms.db.check_db_connection as ochdbcon
"""

import helpers.hsql as hsql

# Start service with
# i oms_docker_up --stage="local"

# From outside
#  psql --host=cf-spm-dev4 --port=5432 -d oms_postgres_db_local

# docker
#  docker run --network oms_postgres_network -it postgres bash -c 'PGPASSWORD=alsdkqoen psql -h oms_postgres -d oms_postgres_db_local --user aljsdalsd -c "SELECT version();"'

# docker compose
# i docker_cmd -c 'PGPASSWORD=alsdkqoen psql -h oms_postgres -d oms_postgres_db_local --user aljsdalsd -c \"SELECT version\(\)\;\"'

# i docker_bash
# > root@5de1a76ba35c:/app# python amp/oms/check_db_connection.py
# DbConnectionInfo(host='oms_postgres', dbname='oms_postgres_db_local', port=5432, user='aljsdalsd', password='alsdkqoen')
# success

file_path = "amp/oms/devops/env/local.oms_db_config.env"

db_connection = hsql.get_connection_info_from_env_file(file_path)
# db_connection = db_connection._replace(host="cf-spm-dev4")
db_connection = db_connection._replace(host="oms_postgres")
# db_connection = db_connection._replace(host="172.16.235.183")
print(db_connection)

hsql.wait_db_connection(*db_connection)
print("success")
