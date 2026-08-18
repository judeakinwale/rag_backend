#!/bin/sh

# update database URLs in .env files to use localhost instead of the default postgres service
sh ./infrastructure/scripts/find_replace.sh ./services/ingest-service/.env postgres:5432 localhost:5432
sh ./infrastructure/scripts/find_replace.sh ./services/rag-service/.env postgres:5432 localhost:5432
sh ./infrastructure/scripts/find_replace.sh ./services/user-service/.env postgres:5432 localhost:5432
sh ./infrastructure/scripts/find_replace.sh ./services/document-processor-service/.env postgres:5432 localhost:5432

echo "Updated database URLs in .env files to use localhost instead of the default postgres service"

# -------------

# activate virtual environment
source ../../bin/activate

# install dependencies
uv pip install -r ./services/ingest-service/requirements.txt
uv pip install greenlet

# -------------

cd ./services/ingest-service/alembic/

# # create a new migration and apply it to the database (in ingest service)
# alembic revision --autogenerate -m "create documents table"
alembic upgrade head

# return to project root
cd ../../../

# -------------

# go to rag-service
cd ./services/rag-service/alembic/

# # create a new migration and apply it to the database (in rag service)
# alembic revision --autogenerate -m "create chats table"
alembic upgrade head

# return to project root
cd ../../../

# -------------

# go to user-service
cd ./services/user-service/alembic/

# # create a new migration and apply it to the database (in user service)
# alembic revision --autogenerate -m "create users table"
alembic upgrade head

# return to project root
cd ../../../

# -------------

# reverse change to database URLs in .env files to use the default postgres service instead of localhost
sh ./infrastructure/scripts/find_replace.sh ./services/ingest-service/.env localhost:5432 postgres:5432
sh ./infrastructure/scripts/find_replace.sh ./services/rag-service/.env localhost:5432 postgres:5432
sh ./infrastructure/scripts/find_replace.sh ./services/user-service/.env localhost:5432 postgres:5432
sh ./infrastructure/scripts/find_replace.sh ./services/document-processor-service/.env localhost:5432 postgres:5432

echo "Reverted database URLs in .env files to use the default postgres service instead of localhost"
