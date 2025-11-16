"""
Servicio de Fine-tuning para OpenAI
Maneja la preparación de datos y entrenamiento de modelos fine-tuned
"""

import json
import logging
from typing import Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class AITrainingService:
    """Servicio para gestionar fine-tuning de modelos OpenAI"""

    def __init__(self, openai_api_key: str):
        """
        Inicializar servicio de fine-tuning

        Args:
            openai_api_key: API key de OpenAI
        """
        self.openai_api_key = openai_api_key
        self.base_url = "https://api.openai.com/v1"

    def _detectar_feedback_negativo(self, feedback: Optional[str]) -> bool:
        """
        Detectar si el feedback es negativo usando palabras clave

        Args:
            feedback: Texto del feedback

        Returns:
            True si el feedback es negativo, False en caso contrario
        """
        if not feedback:
            return False

        feedback_lower = feedback.lower()

        # Palabras clave que indican feedback negativo
        palabras_negativas = [
            "mal",
            "malo",
            "incorrecto",
            "error",
            "equivocado",
            "confuso",
            "no entendí",
            "no entiendo",
            "poco claro",
            "poco clara",
            "incompleto",
            "incompleta",
            "faltante",
            "falta",
            "deficiente",
            "mejorar",
            "debería",
            "deberia",
            "podría",
            "podria",
            "sería mejor",
            "no me gusta",
            "no me sirve",
            "no ayuda",
            "no es útil",
            "muy técnico",
            "muy técnica",
            "demasiado complejo",
            "compleja",
            "no responde",
            "no contesta",
            "no es lo que busco",
            "no es lo que necesito",
        ]

        # Contar palabras negativas
        conteo_negativo = sum(1 for palabra in palabras_negativas if palabra in feedback_lower)

        # Si hay 2 o más palabras negativas, considerar feedback negativo
        return conteo_negativo >= 2

    async def mejorar_respuesta_con_feedback(self, pregunta: str, respuesta: str, feedback: Optional[str]) -> Dict[str, str]:
        """
        Mejorar una respuesta usando el feedback proporcionado

        Args:
            pregunta: Pregunta original
            respuesta: Respuesta original
            feedback: Feedback del usuario sobre la respuesta

        Returns:
            Dict con respuesta_mejorada y mejoras_aplicadas
        """
        if not feedback:
            return {"respuesta_mejorada": respuesta, "mejoras_aplicadas": ["No hay feedback para aplicar"]}

        try:
            prompt_sistema = """Eres un experto en mejorar respuestas de IA basándote en feedback de usuarios.

Tu tarea es mejorar una respuesta considerando el feedback específico proporcionado por el usuario.

INSTRUCCIONES:
1. Analiza el feedback para entender qué aspectos de la respuesta necesitan mejora
2. Mejora la respuesta original incorporando las sugerencias del feedback
3. MANTÉN la información correcta de la respuesta original
4. NO inventes información nueva que no esté en la respuesta original
5. Haz la respuesta más clara, completa o útil según el feedback

FORMATO DE RESPUESTA:
Responde SOLO con un JSON válido en este formato exacto:
{
  "respuesta_mejorada": "...",
  "mejoras_aplicadas": ["mejora 1", "mejora 2", ...]
}

NO incluyas texto adicional fuera del JSON."""

            prompt_usuario = f"""Mejora esta respuesta considerando el feedback del usuario:

PREGUNTA:
{pregunta}

RESPUESTA ORIGINAL:
{respuesta}

FEEDBACK DEL USUARIO:
{feedback}

Por favor, mejora la respuesta incorporando el feedback. Responde SOLO con el JSON solicitado."""

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": prompt_sistema},
                            {"role": "user", "content": prompt_usuario},
                        ],
                        "temperature": 0.3,
                        "max_tokens": 2000,
                    },
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error en OpenAI API mejorando con feedback: {error_msg}")
                    return {"respuesta_mejorada": respuesta, "mejoras_aplicadas": ["Error al mejorar con feedback"]}

                result = response.json()
                contenido = result["choices"][0]["message"]["content"].strip()

                import json

                try:
                    if contenido.startswith("```json"):
                        contenido = contenido.replace("```json", "").replace("```", "").strip()
                    elif contenido.startswith("```"):
                        contenido = contenido.replace("```", "").strip()

                    datos_mejorados = json.loads(contenido)

                    logger.info(f"✅ Respuesta mejorada con feedback. Mejoras: {datos_mejorados.get('mejoras_aplicadas', [])}")

                    return {
                        "respuesta_mejorada": datos_mejorados.get("respuesta_mejorada", respuesta),
                        "mejoras_aplicadas": datos_mejorados.get("mejoras_aplicadas", []),
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando JSON de OpenAI: {e}. Contenido: {contenido}")
                    return {"respuesta_mejorada": respuesta, "mejoras_aplicadas": ["Error al parsear respuesta de IA"]}

        except Exception as e:
            logger.error(f"Error mejorando respuesta con feedback: {e}", exc_info=True)
            return {"respuesta_mejorada": respuesta, "mejoras_aplicadas": [f"Error: {str(e)}"]}

    async def preparar_datos_entrenamiento(
        self, conversaciones: List[Dict], filtrar_feedback_negativo: bool = True
    ) -> Dict[str, str]:
        """
        Preparar datos en formato JSONL para fine-tuning

        Args:
            conversaciones: Lista de conversaciones con pregunta y respuesta
            filtrar_feedback_negativo: Si True, excluye conversaciones con feedback negativo

        Returns:
            Dict con archivo_id, total_conversaciones, y estadísticas de filtrado
        """
        try:
            conversaciones_originales = len(conversaciones)
            conversaciones_filtradas = []
            conversaciones_excluidas = []

            # Filtrar conversaciones con feedback negativo si está habilitado
            for conv in conversaciones:
                feedback = conv.get("feedback")

                if filtrar_feedback_negativo and self._detectar_feedback_negativo(feedback):
                    conversaciones_excluidas.append(
                        {"id": conv.get("id"), "razon": "Feedback negativo detectado", "feedback": feedback}
                    )
                    continue

                conversaciones_filtradas.append(conv)

            if len(conversaciones_filtradas) < 1:
                raise Exception(
                    f"Después del filtrado, solo quedan {len(conversaciones_filtradas)} conversaciones. "
                    f"Se necesita al menos 1. Se excluyeron {len(conversaciones_excluidas)} conversaciones con feedback negativo."
                )

            # Convertir conversaciones a formato JSONL
            jsonl_lines = []
            for conv in conversaciones_filtradas:
                # Mejorar respuesta con feedback si existe
                feedback = conv.get("feedback")
                respuesta = conv["respuesta"]

                if feedback and not self._detectar_feedback_negativo(feedback):
                    # Mejorar respuesta usando feedback positivo
                    mejora_result = await self.mejorar_respuesta_con_feedback(conv["pregunta"], respuesta, feedback)
                    respuesta = mejora_result["respuesta_mejorada"]

                # Formato requerido por OpenAI para fine-tuning
                training_example = {
                    "messages": [
                        {"role": "system", "content": "Eres un asistente útil."},
                        {"role": "user", "content": conv["pregunta"]},
                        {"role": "assistant", "content": respuesta},
                    ]
                }
                jsonl_lines.append(json.dumps(training_example))

            jsonl_content = "\n".join(jsonl_lines)

            # Subir archivo a OpenAI
            async with httpx.AsyncClient(timeout=60.0) as client:
                # Crear archivo temporal en memoria
                files = {"file": ("training_data.jsonl", jsonl_content.encode("utf-8"), "application/jsonl")}
                data = {"purpose": "fine-tune"}

                response = await client.post(
                    f"{self.base_url}/files",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                    files=files,
                    data=data,
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error subiendo archivo a OpenAI: {error_msg}")
                    raise Exception(f"Error subiendo archivo: {error_msg}")

                file_data = response.json()
                file_id = file_data["id"]

                logger.info(
                    f"✅ Archivo subido exitosamente: {file_id} "
                    f"({len(conversaciones_filtradas)} conversaciones de {conversaciones_originales} originales)"
                )

                return {
                    "archivo_id": file_id,
                    "total_conversaciones": len(conversaciones_filtradas),
                    "conversaciones_originales": conversaciones_originales,
                    "conversaciones_excluidas": len(conversaciones_excluidas),
                    "detalles_exclusion": conversaciones_excluidas[:10],  # Primeras 10 para no sobrecargar
                }

        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento: {e}", exc_info=True)
            raise

    async def mejorar_conversacion_para_entrenamiento(self, pregunta: str, respuesta: str) -> Dict[str, str]:
        """
        Mejorar pregunta y respuesta usando IA para optimizar el entrenamiento

        Args:
            pregunta: Pregunta original
            respuesta: Respuesta original

        Returns:
            Dict con pregunta_mejorada y respuesta_mejorada
        """
        try:
            prompt_sistema = """Eres un experto en optimización de datos para fine-tuning de modelos de IA conversacional.

Tu tarea es mejorar preguntas y respuestas para que sean IDEALES para entrenar un modelo de IA que responderá preguntas sobre una base de datos de préstamos y cobranzas.

OBJETIVOS DE MEJORA:
1. **Preguntas**: 
   - Deben ser claras, específicas y directas
   - Deben incluir referencias explícitas a tablas y campos cuando sea relevante (ej: "¿Qué es el campo X en la tabla Y?")
   - Deben usar terminología técnica precisa de la base de datos
   - Deben ser preguntas que un usuario real haría

2. **Respuestas**:
   - Deben ser completas, educativas y precisas
   - Deben incluir contexto sobre tablas y campos mencionados
   - Deben explicar conceptos técnicos de forma clara
   - Deben ser útiles para entrenar al modelo a responder de manera similar
   - Deben mantener el formato original pero mejorado

REGLAS IMPORTANTES:
- MANTÉN el significado original de la pregunta y respuesta
- NO inventes información que no esté en el original
- Si la pregunta menciona una tabla o campo, asegúrate de que la respuesta lo explique claramente
- Usa nombres exactos de tablas y campos (con backticks si es necesario: `tabla`, `campo`)
- Las respuestas deben ser lo suficientemente detalladas para ser educativas
- Optimiza para que el modelo aprenda patrones claros de pregunta-respuesta

FORMATO DE RESPUESTA:
Responde SOLO con un JSON válido en este formato exacto:
{
  "pregunta_mejorada": "...",
  "respuesta_mejorada": "...",
  "mejoras_aplicadas": ["mejora 1", "mejora 2", ...]
}

NO incluyas texto adicional fuera del JSON."""

            prompt_usuario = f"""Mejora esta conversación para fine-tuning:

PREGUNTA ORIGINAL:
{pregunta}

RESPUESTA ORIGINAL:
{respuesta}

Por favor, mejora ambos textos siguiendo las instrucciones del sistema. Responde SOLO con el JSON solicitado."""

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": "gpt-4o-mini",  # Modelo más económico pero efectivo
                        "messages": [
                            {"role": "system", "content": prompt_sistema},
                            {"role": "user", "content": prompt_usuario},
                        ],
                        "temperature": 0.3,  # Baja temperatura para respuestas más consistentes
                        "max_tokens": 2000,
                    },
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error en OpenAI API: {error_msg}")
                    raise Exception(f"Error en OpenAI API: {error_msg}")

                result = response.json()
                contenido = result["choices"][0]["message"]["content"].strip()

                # Intentar parsear JSON
                import json

                try:
                    # Limpiar el contenido si tiene markdown code blocks
                    if contenido.startswith("```json"):
                        contenido = contenido.replace("```json", "").replace("```", "").strip()
                    elif contenido.startswith("```"):
                        contenido = contenido.replace("```", "").strip()

                    datos_mejorados = json.loads(contenido)

                    logger.info(
                        f"✅ Conversación mejorada exitosamente. Mejoras: {datos_mejorados.get('mejoras_aplicadas', [])}"
                    )

                    return {
                        "pregunta_mejorada": datos_mejorados.get("pregunta_mejorada", pregunta),
                        "respuesta_mejorada": datos_mejorados.get("respuesta_mejorada", respuesta),
                        "mejoras_aplicadas": datos_mejorados.get("mejoras_aplicadas", []),
                    }
                except json.JSONDecodeError as e:
                    logger.error(f"Error parseando JSON de OpenAI: {e}. Contenido: {contenido}")
                    # Fallback: devolver original si no se puede parsear
                    return {
                        "pregunta_mejorada": pregunta,
                        "respuesta_mejorada": respuesta,
                        "mejoras_aplicadas": ["Error al parsear respuesta de IA"],
                    }

        except Exception as e:
            logger.error(f"Error mejorando conversación: {e}", exc_info=True)
            raise

    async def iniciar_fine_tuning(
        self,
        archivo_id: str,
        modelo_base: str = "gpt-3.5-turbo",
        epochs: Optional[int] = None,
        learning_rate: Optional[float] = None,
    ) -> Dict:
        """
        Iniciar job de fine-tuning en OpenAI

        Args:
            archivo_id: ID del archivo subido
            modelo_base: Modelo base a usar (gpt-3.5-turbo, gpt-4, etc.)
            epochs: Número de épocas (opcional)
            learning_rate: Learning rate (opcional)

        Returns:
            Dict con información del job
        """
        try:
            payload = {
                "training_file": archivo_id,
                "model": modelo_base,
            }

            if epochs:
                payload["hyperparameters"] = {"n_epochs": epochs}
            if learning_rate:
                if "hyperparameters" not in payload:
                    payload["hyperparameters"] = {}
                payload["hyperparameters"]["learning_rate_multiplier"] = learning_rate

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/fine_tuning/jobs",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error iniciando fine-tuning: {error_msg}")
                    raise Exception(f"Error iniciando fine-tuning: {error_msg}")

                job_data = response.json()
                logger.info(f"✅ Fine-tuning iniciado: {job_data.get('id')}")

                return job_data

        except Exception as e:
            logger.error(f"Error iniciando fine-tuning: {e}", exc_info=True)
            raise

    async def obtener_estado_job(self, job_id: str) -> Dict:
        """
        Obtener estado de un job de fine-tuning

        Args:
            job_id: ID del job en OpenAI

        Returns:
            Dict con estado del job
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/fine_tuning/jobs/{job_id}",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error obteniendo estado del job: {error_msg}")
                    raise Exception(f"Error obteniendo estado: {error_msg}")

                return response.json()

        except Exception as e:
            logger.error(f"Error obteniendo estado del job: {e}", exc_info=True)
            raise

    async def listar_jobs(self, limit: int = 10) -> List[Dict]:
        """
        Listar jobs de fine-tuning

        Args:
            limit: Límite de jobs a retornar

        Returns:
            Lista de jobs
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/fine_tuning/jobs?limit={limit}",
                    headers={"Authorization": f"Bearer {self.openai_api_key}"},
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error listando jobs: {error_msg}")
                    raise Exception(f"Error listando jobs: {error_msg}")

                data = response.json()
                return data.get("data", [])

        except Exception as e:
            logger.error(f"Error listando jobs: {e}", exc_info=True)
            raise
