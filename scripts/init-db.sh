#!/usr/bin/env sh
set -eu
# Local development roles. In production provision independently managed credentials.
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" -v role_password="$POSTGRES_PASSWORD" <<'SQL'
CREATE ROLE graph_writer LOGIN PASSWORD :'role_password';
CREATE ROLE graph_reader LOGIN PASSWORD :'role_password';
GRANT CONNECT ON DATABASE supplygraph TO graph_writer, graph_reader;
GRANT USAGE, CREATE ON SCHEMA public TO graph_writer;
GRANT USAGE ON SCHEMA public TO graph_reader;
ALTER DEFAULT PRIVILEGES FOR ROLE graph_writer IN SCHEMA public GRANT SELECT ON TABLES TO graph_reader;
SQL
