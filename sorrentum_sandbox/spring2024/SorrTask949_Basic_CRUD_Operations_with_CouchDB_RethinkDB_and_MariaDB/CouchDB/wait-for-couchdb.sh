#!/bin/bash
# wait-for-couchdb.sh

set -e

host="$1"
shift
cmd="$@"

until curl -s http://"$host"/ > /dev/null; do
  >&2 echo "CouchDB is unavailable - sleeping"
  sleep 1
done

>&2 echo "CouchDB is up - executing command"
exec $cmd
