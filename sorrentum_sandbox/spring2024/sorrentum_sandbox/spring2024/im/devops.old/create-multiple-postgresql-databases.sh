#!/bin/bash
#
# Create 3 PostgreSQL DBs.
#

# TODO(gp): Not sure it's needed
# TODO(gp): -> create_multistage_psql_dbs.sh

set -e
set -u

echo "Create im_db_dev, im_db_pre_prod, im_db_prod databases..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE im_db_dev;
    CREATE USER im_dev WITH PASSWORD '***REMOVED***';
    GRANT ALL PRIVILEGES ON DATABASE im_db_dev TO im_dev;

    CREATE DATABASE im_db_pre_prod;
    CREATE USER im_pre_prod WITH PASSWORD 'adwaw98dyaw9dWAD0';
    GRANT ALL PRIVILEGES ON DATABASE im_db_pre_prod TO im_pre_prod;

    CREATE DATABASE im_db_prod;
    CREATE USER im_prod WITH PASSWORD 'awdhaw98dyAWPD(WDpa';
    GRANT ALL PRIVILEGES ON DATABASE im_db_prod TO im_prod;
EOSQL
echo "Done"
