# backend/app/api/v1/endpoints/users.py"""Endpoints de gestión de usuariosCRUD completo (solo para ADMIN)"""\nimport
# logging\nfrom datetime \nimport datetime\nfrom fastapi \nimport APIRouter, Depends, HTTPException, status\nfrom
# sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport ( PaginationParams, get_admin_user, get_current_user, get_db,
# get_pagination_params,)\nfrom app.core.security \nimport get_password_hash\nfrom app.models.user \nimport User\nfrom
# app.schemas.user \nimport ( UserCreate, UserListResponse, UserResponse, UserUpdate,)\nfrom app.utils.auditoria_helper
# \nimport ( registrar_creacion, registrar_eliminacion,)\nfrom app.utils.validators \nimport validate_password_strengthlogger
# = logging.getLogger(__name__)router = APIRouter()# ============================================# VERIFICACIÓN DE
# ADMINISTRADORES# ============================================@router.get("/verificar-admin")\ndef
# verificar_rol_administracion(db:\n Session = Depends(get_db)):\n """ 🔍 Verificar estado del rol de administración en el
# sistema """ try:\n # Buscar todos los administradores admins = ( db.query(User).filter(User.is_admin).all() ) # Cambio
# clave:\n rol → is_admin admins_activos = ( db.query(User).filter(User.is_admin, User.is_active).all() ) # Cambio clave:\n
# rol → is_admin # Estadísticas de usuarios por tipo tipos_stats = { "ADMIN":\n { "total":\n
# db.query(User).filter(User.is_admin).count(), "activos":\n db.query(User) .filter(User.is_admin, User.is_active) .count(),
# }, "USER":\n { "total":\n db.query(User).filter(~User.is_admin).count(), "activos":\n db.query(User)
# .filter(~User.is_admin, User.is_active) .count(), }, } # Estado del sistema sistema_funcional = len(admins_activos) > 0
# return { "titulo":\n "🔍 VERIFICACIÓN DEL ROL DE ADMINISTRACIÓN", "fecha_verificacion":\n datetime.now().isoformat(),
# "estado_administracion":\n { "activo":\n sistema_funcional, "total_admins":\n len(admins), "admins_activos":\n
# len(admins_activos), "estado":\n ( "✅ FUNCIONAL" if sistema_funcional else "❌ SIN ADMINISTRADOR ACTIVO" ), },
# "administradores_registrados":\n [ { "id":\n admin.id, "email":\n admin.email, "nombre_completo":\n admin.full_name,
# "activo":\n admin.is_active, "fecha_creacion":\n admin.created_at, "ultimo_login":\n getattr(admin, "last_login", None),
# "estado":\n ( "✅ ACTIVO" if admin.is_active else "❌ INACTIVO" ), } for admin in admins ], "permisos_administrador":\n {
# "gestion_usuarios":\n "✅ Crear, editar, eliminar usuarios", "gestion_clientes":\n "✅ Acceso completo a todos los clientes",
# "gestion_pagos":\n "✅ Modificar, anular pagos sin aprobación", "reportes":\n "✅ Generar todos los reportes",
# "configuracion":\n "✅ Configurar parámetros del sistema", "aprobaciones":\n "✅ Aprobar/rechazar solicitudes",
# "carga_masiva":\n "✅ Realizar migraciones masivas", "auditoria":\n "✅ Ver logs completos del sistema", "dashboard":\n "✅
# Dashboard administrativo completo", }, "estadisticas_usuarios":\n { "por_tipo":\n tipos_stats, "total_usuarios":\n sum(
# stats["total"] for stats in tipos_stats.values() ), "usuarios_activos":\n sum( stats["activos"] for stats in
# tipos_stats.values() ), }, "recomendaciones":\n [ ( "✅ Sistema funcional" if sistema_funcional else "❌ Crear usuario
# administrador" ), ( "🔐 Cambiar contraseñas por defecto" if any( admin.email == "itmaster@rapicreditca.com" for admin in
# admins ) else None ), "👥 Crear usuarios para otros roles según necesidades", "📊 Revisar dashboard administrativo
# regularmente", "🔔 Configurar notificaciones automáticas", ], "acciones_disponibles":\n { "crear_admin":\n "python
# backend/scripts/create_admin.py", "modo_interactivo":\n "python backend/scripts/create_admin.py \ --interactive",
# "listar_admins":\n "python backend/scripts/create_admin.py \ --list", "verificar_sistema":\n "python
# backend/scripts/create_admin.py \ --verify", }, "urls_sistema":\n { "aplicacion":\n "https:\n//pagos-f2qf.onrender.com",
# "documentacion":\n "https:\n//pagos-f2qf.onrender.com/docs", "login":\n "POST /api/v1/auth/login", "dashboard_admin":\n
# "GET /api/v1/dashboard/admin", "verificar_admin":\n "GET /api/v1/users/verificar-admin", }, } except Exception as e:\n
# raise HTTPException( status_code=500, detail=f"Error verificando administración:\n {str(e)}", )@router.post( "/",
# response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Crear usuario",)\ndef create_user( user_data:\n
# UserCreate, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_admin_user),):\n """ Crear un nuevo usuario
# (solo ADMIN) - **email**:\n Email único del usuario - **nombre**:\n Nombre del usuario - **apellido**:\n Apellido del
# usuario - **cargo**:\n Cargo del usuario en la empresa (opcional) - **rol**:\n Rol del usuario (ADMIN, GERENTE, COBRANZAS,
# USER) - **password**:\n Contraseña (mínimo 8 caracteres) - **is_active**:\n Si el usuario está activo """ # Verificar que
# el email no exista existing_user = ( db.query(User).filter(User.email == user_data.email).first() ) if existing_user:\n
# raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya está registrado", ) # Validar fortaleza
# de contraseña is_valid, message = validate_password_strength(user_data.password) if not is_valid:\n raise HTTPException(
# status_code=status.HTTP_400_BAD_REQUEST, detail=message ) # Crear usuario new_user = User( email=user_data.email,
# nombre=user_data.nombre, apellido=user_data.apellido, cargo=user_data.cargo or "Usuario", # Valor por defecto si es None
# is_admin=user_data.is_admin, # Cambio clave:\n rol → is_admin hashed_password=get_password_hash(user_data.password),
# is_active=user_data.is_active, created_at=datetime.utcnow(), ) db.add(new_user) db.commit() db.refresh(new_user) #
# Registrar auditoría try:\n registrar_creacion( db=db, usuario=current_user, modulo="USUARIOS", tabla="usuarios",
# registro_id=new_user.id, descripcion=f"Usuario creado:\n {new_user.email} como {'Administrador' if new_user.is_admin else
# 'Usuario'}", datos_nuevos={ "email":\n new_user.email, "nombre":\n new_user.nombre, "apellido":\n new_user.apellido,
# "is_admin":\n new_user.is_admin, # Cambio clave:\n rol → is_admin "is_active":\n new_user.is_active, }, ) except Exception
# as e:\n logger.warning( f"Error registrando auditoría de creación de usuario:\n {e}" ) return
# new_user@router.get("/test-simple")\ndef test_users_simple(db:\n Session = Depends(get_db)):\n """ Test endpoint simple
# para verificar usuarios (sin autenticación) """ try:\n total_users = db.query(User).count() users =
# db.query(User).limit(5).all() users_data = [] for user in users:\n users_data.append( { "id":\n user.id, "email":\n
# user.email, "nombre":\n user.nombre, "apellido":\n user.apellido, "is_admin":\n user.is_admin, # Cambio clave:\n rol →
# is_admin "is_active":\n user.is_active, "created_at":\n ( user.created_at.isoformat() if user.created_at else None ), } )
# return { "success":\n True, "total_users":\n total_users, "users":\n users_data, "message":\n "Test endpoint funcionando",
# } except Exception as e:\n logger.error(f"Error en test endpoint:\n {str(e)}") return { "success":\n False, "error":\n
# str(e), "message":\n "Error en test endpoint", }@router.get("/test")\ndef test_users_endpoint( db:\n Session =
# Depends(get_db), current_user:\n User = Depends(get_current_user),):\n """ Test endpoint para verificar usuarios """ try:\n
# total_users = db.query(User).count() users = db.query(User).limit(5).all() users_data = [] for user in users:\n
# users_data.append( { "id":\n user.id, "email":\n user.email, "nombre":\n user.nombre, "apellido":\n user.apellido,
# "is_admin":\n user.is_admin, # Cambio clave:\n rol → is_admin "is_active":\n user.is_active, } ) return { "status":\n
# "success", "total_users":\n total_users, "current_user":\n { "id":\n current_user.id, "email":\n current_user.email,
# "is_admin":\n current_user.is_admin, # Cambio clave:\n rol → is_admin }, "users":\n users_data, } except Exception as e:\n
# return { "status":\n "error", "error":\n str(e), "message":\n "Error en test endpoint", }@router.get("/")\ndef list_users(
# db:\n Session = Depends(get_db), pagination:\n PaginationParams = Depends(get_pagination_params), current_user:\n User =
# Depends(get_admin_user), is_active:\n bool = None,):\n """ Listar usuarios con paginación (solo ADMIN) - **page**:\n Número
# de página (default:\n 1) - **page_size**:\n Tamaño de página (default:\n 10, max:\n 100) - **is_active**:\n Filtrar por
# estado activo/inactivo """ query = db.query(User) # Filtros if is_active is not None:\n query = query.filter(User.is_active
# == is_active) # Total total = query.count() # Paginación users =
# query.offset(pagination.skip).limit(pagination.limit).all() return UserListResponse( items=users, total=total,
# page=pagination.page, page_size=pagination.page_size, )@router.get( "/{user_id}", response_model=UserResponse,
# summary="Obtener usuario")\ndef get_user( user_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_admin_user),):\n """ Obtener un usuario por ID (solo ADMIN) """ user = db.query(User).filter(User.id ==
# user_id).first() if not user:\n raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado",
# ) return user@router.put( "/{user_id}", response_model=UserResponse, summary="Actualizar usuario")\ndef update_user(
# user_id:\n int, user_data:\n UserUpdate, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_admin_user),):\n """ Actualizar un usuario (solo ADMIN) Solo se actualizan los campos proporcionados """ user =
# db.query(User).filter(User.id == user_id).first() if not user:\n raise HTTPException(
# status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado", ) # Verificar email único si se está actualizando if
# user_data.email and user_data.email != user.email:\n existing = db.query(User).filter(User.email ==
# user_data.email).first() if existing:\n raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya
# está registrado", ) # Actualizar campos update_data = user_data.model_dump(exclude_unset=True) # Manejar contraseña
# especial - solo actualizar si se proporciona un valor # no vacío if "password" in update_data:\n password_value =
# update_data.pop("password") if password_value and password_value.strip():\n # Solo actualizar contraseña si se proporciona
# un valor no vacío user.hashed_password = get_password_hash(password_value) # Actualizar otros campos for field, value in
# update_data.items():\n setattr(user, field, value) user.updated_at = datetime.utcnow() db.commit() db.refresh(user) return
# user@router.delete( "/{user_id}", status_code=status.HTTP_200_OK, summary="Eliminar usuario")\ndef delete_user( user_id:\n
# int, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_admin_user),):\n """ Eliminar un usuario (HARD
# DELETE - borrado completo de BD) Solo ADMIN puede eliminar usuarios permanentemente """ user =
# db.query(User).filter(User.id == user_id).first() if not user:\n raise HTTPException(
# status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado", ) # No permitir eliminar el propio usuario if
# user.id == current_user.id:\n raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="No puedes desactivar tu
# propio usuario", ) # HARD DELETE - eliminar completamente de la base de datos user_email = user.email # Guardar email para
# log # Registrar auditoría antes de eliminar try:\n registrar_eliminacion( db=db, usuario=current_user, modulo="USUARIOS",
# tabla="usuarios", registro_id=user.id, descripcion=f"Usuario eliminado permanentemente:\n {user_email}", datos_anteriores={
# "email":\n user.email, "nombre":\n user.nombre, "apellido":\n user.apellido, "is_admin":\n user.is_admin, # Cambio clave:\n
# rol → is_admin "is_active":\n user.is_active, }, ) except Exception as e:\n logger.warning( f"Error registrando auditoría
# de eliminación de usuario:\n {e}" ) db.delete(user) db.commit() return { "message":\n f"Usuario {user_email} eliminado
# completamente " f"de la base de datos" }@router.post( "/{user_id}/activate", response_model=UserResponse, summary="Activar
# usuario",)\ndef activate_user( user_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_admin_user),):\n """ Reactivar un usuario desactivado (solo ADMIN) """ user = db.query(User).filter(User.id ==
# user_id).first() if not user:\n raise HTTPException( status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado",
# ) user.is_active = True user.updated_at = datetime.utcnow() db.commit() db.refresh(user) return user@router.post(
# "/{user_id}/deactivate", response_model=UserResponse, summary="Desactivar usuario",)\ndef deactivate_user( user_id:\n int,
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_admin_user),):\n """ Desactivar un usuario (solo ADMIN)
# """ user = db.query(User).filter(User.id == user_id).first() if not user:\n raise HTTPException(
# status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado", ) user.is_active = False user.updated_at =
# datetime.utcnow() db.commit() db.refresh(user) return user
