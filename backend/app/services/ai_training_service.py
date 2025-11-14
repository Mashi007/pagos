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

    async def preparar_datos_entrenamiento(self, conversaciones: List[Dict]) -> Dict[str, str]:
        """
        Preparar datos en formato JSONL para fine-tuning

        Args:
            conversaciones: Lista de conversaciones con pregunta y respuesta

        Returns:
            Dict con archivo_id y total_conversaciones
        """
        try:
            # Convertir conversaciones a formato JSONL
            jsonl_lines = []
            for conv in conversaciones:
                # Formato requerido por OpenAI para fine-tuning
                training_example = {
                    "messages": [
                        {"role": "system", "content": "Eres un asistente útil."},
                        {"role": "user", "content": conv["pregunta"]},
                        {"role": "assistant", "content": conv["respuesta"]},
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

                logger.info(f"✅ Archivo subido exitosamente: {file_id} ({len(conversaciones)} conversaciones)")

                return {
                    "archivo_id": file_id,
                    "total_conversaciones": len(conversaciones),
                }

        except Exception as e:
            logger.error(f"Error preparando datos de entrenamiento: {e}", exc_info=True)
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
