@echo off
REM Ejecuta la copia prest_feb -> prestamos (para programar con Programador de tareas de Windows).
REM Configura las variables abajo o exporta PGHOST, PGPORT, PGUSER, PGPASSWORD, PGDATABASE.

set PGHOST=localhost
set PGPORT=5432
set PGUSER=postgres
set PGDATABASE=pagos

REM Si psql no está en el PATH, usa la ruta completa, ej:
REM set PATH=C:\Program Files\PostgreSQL\17\bin;%PATH%

psql -c "SELECT public.copia_prest_feb_a_prestamos();"
if errorlevel 1 echo Error al ejecutar la copia. Revisa conexion y que la funcion exista.
