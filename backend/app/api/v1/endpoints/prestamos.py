from datetime import date
# Depends, HTTPException, Query\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user,
# get_db\nfrom app.models.cliente \nimport Cliente\nfrom app.models.prestamo \nimport Prestamo\nfrom app.models.user \nimport
# User\nfrom app.schemas.prestamo \nimport ( PrestamoCreate, PrestamoResponse, PrestamoUpdate,)# Constantes de cálculo de
# fechasDAYS_PER_WEEK = 7DAYS_PER_QUINCENA = 15DAYS_PER_MONTH = 30router = APIRouter()\ndef calcular_proxima_fecha_pago
# status_code=201)\ndef crear_prestamo( prestamo:\n PrestamoCreate, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """Crear un nuevo préstamo""" # Verificar que el cliente existe cliente = 
# db.query(Cliente).filter(Cliente.id == prestamo.cliente_id).first() ) if not cliente:\n raise
# HTTPException(status_code=404, detail="Cliente no encontrado") # Calcular próxima fecha de pago proxima_fecha =
# calcular_proxima_fecha_pago( prestamo.fecha_inicio, prestamo.modalidad.value, 0 ) # ✅ CORRECCIÓN:\n usar model_dump() en
# lugar de dict() db_prestamo = Prestamo( **prestamo.model_dump(), saldo_pendiente=prestamo.monto_total, cuotas_pagadas=0,
# proxima_fecha_pago=proxima_fecha, ) db.add(db_prestamo) db.commit() db.refresh(db_prestamo) return
# limit:\n int = Query(20, ge=1, le=1000), cliente_id:\n int = Query(None), estado:\n str = Query(None), db:\n Session =
# obtener_prestamo(prestamo_id:\n int, db:\n Session = Depends(get_db)):\n """Obtener un préstamo por ID""" prestamo =
# db.query(Prestamo).filter(Prestamo.id == prestamo_id).first() if not prestamo:\n raise HTTPException
# detail="Préstamo no encontrado") return prestamo@router.put("/{prestamo_id}", response_model=PrestamoResponse)\ndef
# actualizar_prestamo( prestamo_id:\n int, prestamo_data:\n PrestamoUpdate, db:\n Session = Depends(get_db),):\n
# prestamo:\n raise HTTPException(status_code=404, detail="Préstamo no encontrado") # ✅ CORRECCIÓN:\n usar model_dump() en
# lugar de dict() for field, value in prestamo_data.model_dump(exclude_unset=True).items():\n setattr(prestamo, field, value)
# db.commit() db.refresh(prestamo) return prestamo# TEMPORALMENTE COMENTADO PARA EVITAR ERROR 503# @router.get("/stats")#
# float(monto_total_prestado),# "monto_total_pendiente":\n float(monto_total_pendiente)# }# except Exception as e:\n# raise
# HTTPException(# status_code=500, detail=f"Error:\n {str(e)}")# ENDPOINT TEMPORAL CON DATOS MOCK PARA EVITAR ERROR
# HTTPException( status_code=500, detail=f"Error al obtener estadísticas:\n {str(e)}", )
