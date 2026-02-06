#!/bin/sh
# Ejecuta la copia prest_feb -> prestamos (para programar con cron).
# Configura las variables abajo o exporta PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE.

export PGHOST="${PGHOST:-localhost}"
export PGPORT="${PGPORT:-5432}"
export PGUSER="${PGUSER:-postgres}"
export PGDATABASE="${PGDATABASE:-pagos}"

psql -c "SELECT public.copia_prest_feb_a_prestamos();"
