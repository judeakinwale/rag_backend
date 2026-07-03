#!/bin/sh
set -e

# the env variable names are set in the official postgres image, and defaults to "postgres_*"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE user_db OWNER "$POSTGRES_USER";
    CREATE DATABASE ingest_db OWNER "$POSTGRES_USER";
    CREATE DATABASE notification_db OWNER "$POSTGRES_USER";
EOSQL
