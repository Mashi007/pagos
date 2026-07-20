# -*- coding: utf-8 -*-
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend/app/api/v1/endpoints/notificaciones/routes.py"
t = p.read_text(encoding="utf-8")
start = t.find("VARIABLES_PRECARGADAS = [")
end = t.find('@router.get("")\ndef get_notificaciones_lista(', start)
if start < 0 or end < 0:
    raise SystemExit(f"markers not found start={start} end={end}")

new_block = '''VARIABLES_PRECARGADAS = [
    {
        "nombre_variable": "nombre",
        "tabla": "clientes",
        "campo_bd": "nombres",
        "descripcion": "Nombre del cliente (token {{nombre}} en plantillas)",
    },
    {"nombre_variable": "nombre_cliente", "tabla": "clientes", "campo_bd": "nombres", "descripcion": "Nombres del cliente"},
    {"nombre_variable": "cedula", "tabla": "clientes", "campo_bd": "cedula", "descripcion": "Cedula de identidad"},
    {"nombre_variable": "telefono", "tabla": "clientes", "campo_bd": "telefono", "descripcion": "Telefono de contacto"},
    {"nombre_variable": "email", "tabla": "clientes", "campo_bd": "email", "descripcion": "Correo electronico"},
    {"nombre_variable": "numero_cuota", "tabla": "cuotas", "campo_bd": "numero_cuota", "descripcion": "Numero de cuota"},
    {"nombre_variable": "fecha_vencimiento", "tabla": "cuotas", "campo_bd": "fecha_vencimiento", "descripcion": "Fecha de vencimiento"},
    {
        "nombre_variable": "fecha_vencimiento_display",
        "tabla": "cuotas",
        "campo_bd": "fecha_vencimiento",
        "descripcion": "Fecha de vencimiento legible",
    },
    {"nombre_variable": "monto_cuota", "tabla": "cuotas", "campo_bd": "monto", "descripcion": "Monto de la cuota"},
    {
        "nombre_variable": "monto",
        "tabla": "cuotas",
        "campo_bd": "monto",
        "descripcion": "Monto de la cuota (alias {{monto}})",
    },
    {
        "nombre_variable": "dias_atraso",
        "tabla": "cuotas",
        "campo_bd": "dias_mora",
        "descripcion": "Dias desde vencimiento de la cuota de referencia (1/3/5/30; tipo de envio)",
    },
    {
        "nombre_variable": "cuotas_atrasadas",
        "tabla": "prestamos",
        "campo_bd": "conteo",
        "descripcion": "Cantidad de cuotas en atraso del prestamo (misma regla que estado de cuenta)",
    },
]


@router.post("/variables/inicializar-precargadas")
def inicializar_variables_precargadas(db: Session = Depends(get_db)):
    """Inserta variables precargadas si no existen (por nombre_variable). Idempotente.
    Tambien asegura plantilla unica PREJUDICIAL y su vinculo en envios."""
    creadas = 0
    existentes = 0
    for item in VARIABLES_PRECARGADAS:
        nombre = item["nombre_variable"]
        existing = db.execute(select(VariableNotificacion).where(VariableNotificacion.nombre_variable == nombre)).scalar_one_or_none()
        if existing:
            existentes += 1
            continue
        try:
            v = VariableNotificacion(
                nombre_variable=nombre,
                tabla=item["tabla"],
                campo_bd=item["campo_bd"],
                descripcion=item.get("descripcion"),
                activa=True,
            )
            db.add(v)
            db.commit()
            creadas += 1
        except Exception as e:
            db.rollback()
            logger.warning("inicializar_variables_precargadas: %s para %s", e, nombre)

    prejudicial_info: dict = {}
    try:
        from app.services.notificacion_plantilla_prejudicial import asegurar_modulo_prejudicial

        prejudicial_info = asegurar_modulo_prejudicial(db, forzar_contenido_plantilla=False)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("inicializar_variables_precargadas: modulo PREJUDICIAL: %s", e)

    total = creadas + existentes
    return {
        "mensaje": f"Variables precargadas: {creadas} creadas, {existentes} ya existian.",
        "variables_creadas": creadas,
        "variables_existentes": existentes,
        "total": total,
        "prejudicial": prejudicial_info,
    }


@router.post("/plantillas/asegurar-prejudicial")
def asegurar_plantilla_prejudicial_endpoint(
    forzar_contenido: bool = Query(False, description="Reescribe asunto/cuerpo de la plantilla canonica"),
    db: Session = Depends(get_db),
):
    """
    Genera/actualiza variables del modulo, la plantilla unica PREJUDICIAL
    ({{nombre}}) y vincula plantilla_id en notificaciones_envios si falta.
    """
    try:
        from app.services.notificacion_plantilla_prejudicial import asegurar_modulo_prejudicial

        info = asegurar_modulo_prejudicial(db, forzar_contenido_plantilla=forzar_contenido)
        db.commit()
        return {
            "mensaje": "Modulo PREJUDICIAL configurado (variables + plantilla unica).",
            **info,
        }
    except Exception as e:
        db.rollback()
        logger.exception("asegurar_plantilla_prejudicial_endpoint: %s", e)
        raise HTTPException(status_code=500, detail="Error al asegurar plantilla PREJUDICIAL")


'''

t2 = t[:start] + new_block + t[end:]
p.write_text(t2, encoding="utf-8")
print("OK replaced VARIABLES_PRECARGADAS + endpoints")
