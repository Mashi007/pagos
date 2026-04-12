"""
Excel Prestamos Drive: snapshot hoja CONCILIACIÓN filtrado por columna LOTE.
"""
from __future__ import annotations

import json
import logging
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, JSONResponse, HTMLResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.conciliacion_sheet import ConciliacionSheetMeta
from app.services.reporte_clientes_hoja import parse_lotes_query
from app.services.reporte_prestamos_drive import build_prestamos_drive_excel

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/exportar/prestamos-drive/debug-headers", include_in_schema=False)
def debug_prestamos_drive_headers(
    db: Session = Depends(get_db),
):
    """
    DEBUG: Muestra las cabeceras detectadas en la hoja CONCILIACIÓN.
    Útil para diagnóstico cuando falla la detección de columnas.
    """
    meta = db.get(ConciliacionSheetMeta, 1)
    headers = list(meta.headers) if meta and meta.headers else []
    
    logger.warning(
        "=== DEBUG HEADERS CONCILIACIÓN ===\n"
        "Total de cabeceras: %d\n"
        "Headers:\n%s",
        len(headers),
        json.dumps(headers, ensure_ascii=False, indent=2),
    )
    
    html_content = f"""
    <html>
    <head>
        <title>Debug - Headers CONCILIACIÓN</title>
        <style>
            body {{ font-family: monospace; padding: 20px; background: #f5f5f5; }}
            h1 {{ color: #333; }}
            .container {{ background: white; padding: 20px; border-radius: 5px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
            th {{ background-color: #4CAF50; color: white; }}
            tr:nth-child(even) {{ background-color: #f2f2f2; }}
            .warning {{ background-color: #fff3cd; padding: 10px; border-radius: 3px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔍 Debug: Headers de la Hoja CONCILIACIÓN</h1>
            
            <div class="warning">
                <strong>⚠️ Información de diagnóstico:</strong> Copia estos valores exactos para reportar el problema.
            </div>
            
            <h2>Total de columnas: {len(headers)}</h2>
            
            <table>
                <thead>
                    <tr>
                        <th>Índice</th>
                        <th>Nombre Original</th>
                        <th>Longitud</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    for i, h in enumerate(headers, 1):
        html_content += f"""
                    <tr>
                        <td>{i}</td>
                        <td><code>{h or '(vacío)'}</code></td>
                        <td>{len(h) if h else 0}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
            
            <h2>JSON para copiar:</h2>
            <pre>
    """
    
    html_content += json.dumps(headers, ensure_ascii=False, indent=2)
    
    html_content += """
            </pre>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)


@router.get("/exportar/prestamos-drive")
def exportar_prestamos_drive_excel(
    db: Session = Depends(get_db),
    lotes: str = Query("", description="Lotes separados por coma (columna LOTE en la hoja), ej. 70 o 70,71"),
):
    """
    Descarga Excel desde conciliacion_sheet_rows (misma fuente que Clientes hoja).
    Columnas: cedula, total_financiamiento, abonos, modalidad_pago, fecha_requerimiento,
    fecha_aprobacion, producto, concesionario, analista, modelo_vehiculo, numero_cuotas.
    Solo filas cuyo LOTE coincide con uno de los valores en `lotes`.
    """
    logger.info("[prestamos_drive] GET /exportar/prestamos-drive lotes=%r", lotes)
    try:
        lo = parse_lotes_query(lotes)
        content, n = build_prestamos_drive_excel(db, lo)
    except ValueError as e:
        logger.warning("[prestamos_drive] GET 400/404: %s", e)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("[prestamos_drive] GET error: %s", e)
        raise HTTPException(
            status_code=500,
            detail="Error al generar el reporte Préstamos Drive.",
        ) from e

    hoy_str = date.today().isoformat()
    lpart = "-".join(str(x) for x in sorted(set(lo)))
    fname = f"Prestamos_drive_CONCILIACION_lotes_{lpart}_{hoy_str}.xlsx"
    logger.info("[prestamos_drive] GET OK filas=%s bytes=%s", n, len(content))
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )
