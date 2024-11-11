#!bin/sh

POSTGRES_CONNECTION_STRING=$(cat /secret/cfg/config.json | jq -r '.db.conninfo')

psql -d $POSTGRES_CONNECTION_STRING -f ./delete_expired_messages.sql