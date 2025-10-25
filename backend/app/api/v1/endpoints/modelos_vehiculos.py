# typing \nimport List, Optional\nfrom fastapi \nimport APIRouter, Depends, HTTPException, Query\nfrom sqlalchemy \nimport
# or_\nfrom sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport get_current_user, get_db\nfrom
# app.models.modelo_vehiculo \nimport ModeloVehiculo\nfrom app.models.user \nimport User\nfrom app.schemas.modelo_vehiculo
# \nimport ( ModeloVehiculoCreate, ModeloVehiculoListResponse, ModeloVehiculoResponse, ModeloVehiculoUpdate,)router =
# APIRouter()logger = logging.getLogger(__name__)@router.get("/", response_model=ModeloVehiculoListResponse)\ndef
# Query(20, ge=1, le=1000, description="Tamaño de página"), # Búsqueda search:\n Optional[str] = Query(None,
# query = query.filter( or_(ModeloVehiculo.modelo.ilike(f"%{search}%")) ) if activo is not None:\n query =
# query.filter(ModeloVehiculo.activo == activo) # Ordenar por modelo query = query.order_by(ModeloVehiculo.modelo) # Contar
# detail="Error interno del servidor" )@router.get("/{modelo_id}", response_model=ModeloVehiculoResponse)\ndef
# obtener_modelo_vehiculo( modelo_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_current_user),):\n """ 🔍 Obtener un modelo de vehículo por ID """ try:\n modelo = ( db.query(ModeloVehiculo)
# .filter(ModeloVehiculo.id == modelo_id) .first() ) if not modelo:\n raise HTTPException( status_code=404, detail="Modelo de
# vehículo no encontrado" ) return ModeloVehiculoResponse.model_validate(modelo) except HTTPException:\n raise except
# Exception as e:\n logger.error(f"Error obteniendo modelo {modelo_id}:\n {e}") raise HTTPException( status_code=500,
# modelo_data:\n ModeloVehiculoCreate, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n
# """ ➕ Crear un nuevo modelo de vehículo """ try:\n # Verificar si ya existe un modelo con el mismo nombre existing_modelo =
# ( db.query(ModeloVehiculo) .filter(ModeloVehiculo.modelo.ilike(modelo_data.modelo)) .first() ) if existing_modelo:\n raise
# HTTPException( status_code=400, detail="Ya existe un modelo de vehículo con ese nombre", ) # Crear nuevo modelo
# nuevo_modelo = ModeloVehiculo( modelo=modelo_data.modelo.strip(), activo=modelo_data.activo ) db.add(nuevo_modelo)
# db.commit() db.refresh(nuevo_modelo) logger.info( f"Modelo de vehículo" + f"creado:\n {nuevo_modelo.modelo} (ID:\n
# {nuevo_modelo.id})" ) return ModeloVehiculoResponse.model_validate(nuevo_modelo) except HTTPException:\n raise except
# Exception as e:\n db.rollback() logger.error(f"Error creando modelo de vehículo:\n {e}") raise HTTPException(
# status_code=500, detail="Error interno del servidor" )@router.put("/{modelo_id}",
# response_model=ModeloVehiculoResponse)\ndef actualizar_modelo_vehiculo( modelo_id:\n int, modelo_data:\n
# ModeloVehiculoUpdate, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ ✏️
# Actualizar un modelo de vehículo existente """ try:\n # Buscar modelo existente modelo = ( db.query(ModeloVehiculo)
# .filter(ModeloVehiculo.id == modelo_id) .first() ) if not modelo:\n raise HTTPException( status_code=404, detail="Modelo de
# vehículo no encontrado" ) # Verificar nombre único si se está cambiando if modelo_data.modelo and modelo_data.modelo !=
# modelo.modelo:\n existing_modelo = ( db.query(ModeloVehiculo) .filter( ModeloVehiculo.modelo.ilike(modelo_data.modelo),
# ModeloVehiculo.id != modelo_id, ) .first() ) if existing_modelo:\n raise HTTPException( status_code=400, detail="Ya existe
# modelo_data.modelo.strip() if modelo_data.activo is not None:\n modelo.activo = modelo_data.activo db.commit()
# db.refresh(modelo) logger.info( f"Modelo de vehículo actualizado:\n {modelo.modelo} (ID:\n {momodelo.id})" ) return
# ModeloVehiculoResponse.model_validate(modelo) except HTTPException:\n raise except Exception as e:\n db.rollback()
# logger.error(f"Error actualizando modelo {modelo_id}:\n {e}") raise HTTPException( status_code=500, detail="Error interno
# del servidor" )@router.delete("/{modelo_id}")\ndef eliminar_modelo_vehiculo( modelo_id:\n int, db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ 🗑️ Eliminar un modelo de vehículo (HARD DELETE -
# borrado completo de BD) """ try:\n # Buscar modelo existente modelo = ( db.query(ModeloVehiculo) .filter(ModeloVehiculo.id
# == modelo_id) .first() ) if not modelo:\n raise HTTPException( status_code=404, detail="Modelo de vehículo no encontrado" )
# db.delete(modelo) db.commit() logger.info( f"Modelo de vehículo ELIMINADO COMPLETAMENTE:\n {modelo_nombre} (ID:\n
# HTTPException:\n raise except Exception as e:\n db.rollback() logger.error(f"Error eliminando modelo {modelo_id}:\n {e}")
# raise HTTPException( status_code=500, detail="Error interno del servidor" )
