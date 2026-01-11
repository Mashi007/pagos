"""
Servicio para Chat AI - Encapsula toda la lógica de procesamiento de preguntas AI
Refactorización para reducir complejidad ciclomática
"""

import logging
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class AIChatService:
    """Servicio para manejar el Chat AI con acceso a base de datos"""

    def __init__(self, db: Session):
        self.db = db
        self.config_dict: Optional[Dict[str, str]] = None
        self.openai_api_key: Optional[str] = None
        self.modelo: str = "gpt-3.5-turbo"
        self.temperatura: float = 0.7
        self.max_tokens: int = 2000
        self.timeout: float = 60.0

    def inicializar_configuracion(self) -> None:
        """Obtiene y valida la configuración de AI"""
        from app.api.v1.endpoints.configuracion import (
            _obtener_configuracion_ai_con_reintento,
            _validar_configuracion_ai,
        )

        configs = _obtener_configuracion_ai_con_reintento(self.db)
        if not configs:
            raise HTTPException(status_code=400, detail="No hay configuracion de AI")

        self.config_dict = {config.clave: config.valor for config in configs}
        _validar_configuracion_ai(self.config_dict)

        # Extraer parámetros de configuración
        # Desencriptar API Key si está encriptada
        from app.core.encryption import decrypt_api_key

        encrypted_api_key = self.config_dict.get("openai_api_key", "")
        self.openai_api_key = decrypt_api_key(encrypted_api_key) if encrypted_api_key else ""

        # ✅ PRIORIDAD: Si hay un modelo fine-tuned activo, usarlo en lugar del modelo base
        modelo_fine_tuned = self.config_dict.get("modelo_fine_tuned", "")
        if modelo_fine_tuned and modelo_fine_tuned.strip():
            self.modelo = modelo_fine_tuned.strip()
            logger.info(f"✅ Usando modelo fine-tuned activo: {self.modelo}")
        else:
            self.modelo = self.config_dict.get("modelo", "gpt-3.5-turbo")
            logger.debug(f"Usando modelo base: {self.modelo}")

        self.temperatura = float(self.config_dict.get("temperatura", "0.7"))
        self.max_tokens = int(self.config_dict.get("max_tokens", "2000"))
        # ✅ Timeout configurable desde BD (en segundos)
        self.timeout = float(self.config_dict.get("timeout_segundos", "60.0"))

    def validar_pregunta(self, pregunta: str) -> str:
        """
        Valida y normaliza la pregunta.
        Retorna la pregunta normalizada.
        """
        from app.api.v1.endpoints.configuracion import _validar_pregunta_es_sobre_bd

        pregunta = pregunta.strip()
        if not pregunta:
            raise HTTPException(status_code=400, detail="La pregunta no puede estar vacia")

        # ✅ Validar tamaño máximo de pregunta (default: 2000 caracteres)
        max_length = int(self.config_dict.get("max_pregunta_length", "2000")) if self.config_dict else 2000
        if len(pregunta) > max_length:
            raise HTTPException(status_code=400, detail=f"La pregunta no puede exceder {max_length} caracteres")

        _validar_pregunta_es_sobre_bd(pregunta)
        return pregunta

    def _obtener_resumen_bd_con_cache(self, ttl: int) -> str:
        """
        Obtiene el resumen de BD usando cache para mejorar rendimiento.

        Args:
            ttl: Tiempo de vida del cache en segundos

        Returns:
            Resumen de BD como string
        """
        from app.api.v1.endpoints.configuracion import _obtener_resumen_bd
        from app.core.cache import cache_backend

        cache_key = "ai_chat:resumen_bd"

        # Intentar obtener del cache
        cached_result = cache_backend.get(cache_key)
        if cached_result is not None:
            logger.debug(f"✅ Cache HIT: resumen_bd (TTL restante: {ttl}s)")
            return cached_result

        # Cache MISS: obtener de BD
        logger.debug(f"❌ Cache MISS: resumen_bd - Obteniendo de BD...")
        resumen_bd = _obtener_resumen_bd(self.db)

        # Guardar en cache
        cache_backend.set(cache_key, resumen_bd, ttl=ttl)
        logger.debug(f"💾 Cache guardado: resumen_bd (TTL: {ttl}s)")

        return resumen_bd

    async def obtener_contexto_completo_async(self, pregunta: str) -> Dict[str, str]:
        """
        Versión async para obtener contexto completo.
        Incluye llamada async a documentos semánticos.
        """
        from app.api.v1.endpoints.configuracion import (
            _ejecutar_consulta_dinamica,
            _extraer_cedula_de_pregunta,
            _obtener_contexto_documentos_semantico,
            _obtener_datos_adicionales,
            _obtener_info_cliente_por_cedula,
            _obtener_info_esquema,
            _obtener_resumen_bd,
        )

        pregunta_lower = pregunta.lower().strip()

        # ✅ Obtener contexto base con cache
        # Cache TTL configurable desde BD (default: 5 minutos = 300 segundos)
        cache_ttl = int(self.config_dict.get("cache_resumen_bd_ttl", "300"))
        resumen_bd = self._obtener_resumen_bd_con_cache(cache_ttl)
        info_esquema = _obtener_info_esquema(pregunta_lower, self.db)

        # Obtener contexto de documentos (async)
        contexto_documentos = ""
        if self.openai_api_key:
            try:
                contexto_documentos, _ = await _obtener_contexto_documentos_semantico(pregunta, self.openai_api_key, self.db)
            except Exception as e:
                logger.warning(f"Error obteniendo contexto de documentos: {e}")

        # Búsqueda por cédula si aplica
        busqueda_cedula = _extraer_cedula_de_pregunta(pregunta)
        info_cliente_buscado = ""
        if busqueda_cedula:
            info_cliente_buscado = _obtener_info_cliente_por_cedula(busqueda_cedula, self.db)

        # Datos adicionales (cálculos, ML, etc.)
        datos_adicionales = _obtener_datos_adicionales(pregunta, pregunta_lower, self.db)

        # ✅ NUEVO: Ejecutar consultas dinámicas basadas en la pregunta
        consultas_dinamicas = _ejecutar_consulta_dinamica(pregunta, pregunta_lower, self.db)

        return {
            "resumen_bd": resumen_bd,
            "info_esquema": info_esquema,
            "contexto_documentos": contexto_documentos,
            "info_cliente_buscado": info_cliente_buscado,
            "datos_adicionales": datos_adicionales,
            "consultas_dinamicas": consultas_dinamicas,
        }

    def construir_system_prompt(self, contexto: Dict[str, str]) -> str:
        """
        Construye el system prompt usando configuración personalizada o default.
        """
        from app.api.v1.endpoints.configuracion import (
            _construir_system_prompt_default,
            _construir_system_prompt_personalizado,
            _obtener_variables_personalizadas,
        )

        prompt_personalizado = self.config_dict.get("system_prompt_personalizado", "")
        usar_prompt_personalizado = prompt_personalizado and prompt_personalizado.strip()

        if usar_prompt_personalizado:
            logger.info("Usando prompt personalizado configurado por el usuario")
            variables_personalizadas = _obtener_variables_personalizadas(self.db)
            return _construir_system_prompt_personalizado(
                prompt_personalizado,
                contexto["resumen_bd"],
                contexto["info_cliente_buscado"],
                contexto["datos_adicionales"],
                contexto["info_esquema"],
                contexto["contexto_documentos"],
                variables_personalizadas,
            )
        else:
            return _construir_system_prompt_default(
                contexto["resumen_bd"],
                contexto["info_cliente_buscado"],
                contexto["datos_adicionales"],
                contexto["info_esquema"],
                contexto["contexto_documentos"],
                contexto.get("consultas_dinamicas", ""),
            )

    async def llamar_openai_api(self, system_prompt: str, pregunta: str) -> Dict[str, Any]:
        """
        Llama a la API de OpenAI y retorna la respuesta.
        """
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.modelo,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": pregunta},
                        ],
                        "temperature": self.temperatura,
                        "max_tokens": self.max_tokens,
                    },
                )

                elapsed_time = time.time() - start_time

                if response.status_code == 200:
                    result = response.json()
                    respuesta_ai = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                    tokens_usados = result.get("usage", {}).get("total_tokens", 0)

                    logger.info(f"Chat AI exitoso: {tokens_usados} tokens usados en {elapsed_time:.2f}s")

                    return {
                        "success": True,
                        "respuesta": respuesta_ai,
                        "pregunta": pregunta,
                        "tokens_usados": tokens_usados,
                        "modelo_usado": self.modelo,
                        "tiempo_respuesta": round(elapsed_time, 2),
                    }
                else:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get("error", {}).get("message", "Error desconocido")

                    logger.error(f"Error en Chat AI: {error_message}")

                    return {
                        "success": False,
                        "respuesta": f"Error de OpenAI: {error_message}",
                        "error": error_message,
                        "pregunta": pregunta,
                    }

        except httpx.TimeoutException:
            elapsed_time = time.time() - start_time
            logger.error(f"Timeout en Chat AI (Tiempo: {elapsed_time:.2f}s, Límite: {self.timeout}s)")
            return {
                "success": False,
                "respuesta": f"Timeout al conectar con OpenAI (limite: {self.timeout}s). La pregunta puede ser muy compleja.",
                "error": "TIMEOUT",
                "pregunta": pregunta,
            }
        except Exception as e:
            elapsed_time = time.time() - start_time
            logger.error(f"Error en Chat AI: {str(e)} (Tiempo: {elapsed_time:.2f}s)")
            return {
                "success": False,
                "respuesta": f"Error: {str(e)}",
                "error": str(e),
                "pregunta": pregunta,
            }

    async def procesar_pregunta(self, pregunta: str) -> Dict[str, Any]:
        """
        Procesa una pregunta completa: valida, obtiene contexto, construye prompt y llama a OpenAI.
        """
        # Validar pregunta
        pregunta = self.validar_pregunta(pregunta)

        # Obtener contexto completo
        contexto = await self.obtener_contexto_completo_async(pregunta)

        # Construir system prompt
        system_prompt = self.construir_system_prompt(contexto)

        if contexto["contexto_documentos"]:
            logger.info(f"Contexto de documentos incluido en system_prompt: {len(contexto['contexto_documentos'])} caracteres")

        # Llamar a OpenAI API
        return await self.llamar_openai_api(system_prompt, pregunta)
