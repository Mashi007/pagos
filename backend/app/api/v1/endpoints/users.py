from datetime import date
# sqlalchemy.orm \nimport Session\nfrom app.api.deps \nimport 
# get_pagination_params,)\nfrom app.core.security \nimport get_password_hash\nfrom app.models.user \nimport User\nfrom
# app.schemas.user \nimport ( UserCreate, UserListResponse, UserResponse, UserUpdate,)\nfrom app.utils.auditoria_helper
# \nimport ( registrar_creacion, registrar_eliminacion,)\nfrom app.utils.validators \nimport validate_password_strengthlogger
# = logging.getLogger(__name__)router = APIRouter()# ============================================# VERIFICACIÓN DE
# ADMINISTRADORES# ============================================@router.get("/verificar-admin")\ndef
# verificar_rol_administracion(db:\n Session = Depends(get_db)):\n """ 🔍 Verificar estado del rol de administración en el
# "activo":\n admin.is_active, "fecha_creacion":\n admin.created_at, "ultimo_login":\n getattr(admin, "last_login", None),
# administrador" ), 
# response_model=UserResponse, status_code=status.HTTP_201_CREATED, summary="Crear usuario",)\ndef create_user
# UserCreate, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_admin_user),):\n """ Crear un nuevo usuario
# (solo ADMIN) - **email**:\n Email único del usuario - **nombre**:\n Nombre del usuario - **apellido**:\n Apellido del
# usuario - **cargo**:\n Cargo del usuario en la empresa (opcional) - **rol**:\n Rol del usuario 
# USER) - **password**:\n Contraseña (mínimo 8 caracteres) - **is_active**:\n Si el usuario está activo """ # Verificar que
# el email no exista existing_user = ( db.query(User).filter(User.email == user_data.email).first() ) if existing_user:\n
# raise HTTPException( status_code=status.HTTP_400_BAD_REQUEST, detail="El email ya está registrado", ) # Validar fortaleza
# de contraseña is_valid, message = validate_password_strength(user_data.password) if not is_valid:\n raise HTTPException
# status_code=status.HTTP_400_BAD_REQUEST, detail=message ) # Crear usuario new_user = User
# is_admin=user_data.is_admin, # Cambio clave:\n rol → is_admin hashed_password=get_password_hash(user_data.password),
# registro_id=new_user.id, descripcion=f"Usuario creado:\n {new_user.email} como 
# "is_admin":\n new_user.is_admin, # Cambio clave:\n rol → is_admin "is_active":\n new_user.is_active, }, ) except Exception
# as e:\n logger.warning( f"Error registrando auditoría de creación de usuario:\n {e}" ) return
# new_user@router.get("/test-simple")\ndef test_users_simple(db:\n Session = Depends(get_db)):\n """ Test endpoint simple
# db.query(User).limit(5).all() users_data = [] for user in users:\n users_data.append
# is_admin "is_active":\n user.is_active, "created_at":\n ( user.created_at.isoformat() if user.created_at else None ), } )
# return 
# } except Exception as e:\n logger.error(f"Error en test endpoint:\n {str(e)}") return 
# str(e), "message":\n "Error en test endpoint", }@router.get("/test")\ndef test_users_endpoint
# total_users = db.query(User).count() users = db.query(User).limit(5).all() users_data = [] for user in users:\n
# users_data.append
# "is_admin":\n user.is_admin, # Cambio clave:\n rol → is_admin "is_active":\n user.is_active, } ) return 
# "is_admin":\n current_user.is_admin, # Cambio clave:\n rol → is_admin }, "users":\n users_data, } except Exception as e:\n
# return { "status":\n "error", "error":\n str(e), "message":\n "Error en test endpoint", }@router.get("/")\ndef list_users
# db:\n Session = Depends(get_db), pagination:\n PaginationParams = Depends(get_pagination_params), current_user:\n User =
# de página (default:\n 1) - **page_size**:\n Tamaño de página (default:\n 10, max:\n 100) - **is_active**:\n Filtrar por
# == is_active) # Total total = query.count() # Paginación users =
# query.offset(pagination.skip).limit(pagination.limit).all() return UserListResponse
# page=pagination.page, page_size=pagination.page_size, )@router.get
# summary="Obtener usuario")\ndef get_user( user_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_admin_user),):\n """ Obtener un usuario por ID (solo ADMIN) """ user = db.query(User).filter
# user_id).first() if not user:\n raise HTTPException
# ) return user@router.put( "/{user_id}", response_model=UserResponse, summary="Actualizar usuario")\ndef update_user
# user_id:\n int, user_data:\n UserUpdate, db:\n Session = Depends(get_db), current_user:\n User =
# db.query(User).filter(User.id == user_id).first() if not user:\n raise HTTPException
# status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado", ) # Verificar email único si se está actualizando if
# user_data.email and user_data.email != user.email:\n existing = db.query(User).filter
# user_data.email).first() if existing:\n raise HTTPException
# update_data.pop("password") if password_value and password_value.strip():\n # Solo actualizar contraseña si se proporciona
# user@router.delete( "/{user_id}", status_code=status.HTTP_200_OK, summary="Eliminar usuario")\ndef delete_user
# int, db:\n Session = Depends(get_db), current_user:\n User = Depends(get_admin_user),):\n """ Eliminar un usuario 
# db.query(User).filter(User.id == user_id).first() if not user:\n raise HTTPException
# status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado", ) # No permitir eliminar el propio usuario if
# user.id == current_user.id:\n raise HTTPException
# rol → is_admin "is_active":\n user.is_active, }, ) except Exception as e:\n logger.warning
# de eliminación de usuario:\n {e}" ) db.delete(user) db.commit() return { "message":\n f"Usuario {user_email} eliminado
# usuario",)\ndef activate_user( user_id:\n int, db:\n Session = Depends(get_db), current_user:\n User =
# Depends(get_admin_user),):\n """ Reactivar un usuario desactivado (solo ADMIN) """ user = db.query(User).filter
# user_id).first() if not user:\n raise HTTPException
# "/{user_id}/deactivate", response_model=UserResponse, summary="Desactivar usuario",)\ndef deactivate_user
# db:\n Session = Depends(get_db), current_user:\n User = Depends(get_admin_user),):\n """ Desactivar un usuario (solo ADMIN)
# """ user = db.query(User).filter(User.id == user_id).first() if not user:\n raise HTTPException
# status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado", ) user.is_active = False user.updated_at =

"""