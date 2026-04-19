-- Auditoría: cada exportación Excel desde Notificaciones > Clientes (Drive)
-- (POST /api/v1/clientes/drive-import/exportar-excel) inserta aquí y borra las filas en public.drive.

CREATE TABLE IF NOT EXISTS public.clientes_drive_export_excel_auditoria (
    id SERIAL PRIMARY KEY,
    exportado_en TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    usuario_email VARCHAR(255) NOT NULL,
    modo VARCHAR(40) NOT NULL,
    filas_count INTEGER NOT NULL,
    sheet_rows_json TEXT NULL
);

CREATE INDEX IF NOT EXISTS ix_clientes_drive_export_excel_auditoria_exportado_en
    ON public.clientes_drive_export_excel_auditoria (exportado_en DESC);

COMMENT ON TABLE public.clientes_drive_export_excel_auditoria IS
    'Registro de exportaciones Excel de candidatos Drive; las filas exportadas se eliminan de public.drive hasta el próximo sync.';
