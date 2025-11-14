"""
Servicio RAG (Retrieval-Augmented Generation)
Maneja la generación de embeddings y búsqueda semántica
"""

import logging
from typing import Dict, List, Optional

import httpx
import numpy as np

logger = logging.getLogger(__name__)


class RAGService:
    """Servicio para gestión de embeddings y búsqueda semántica"""

    def __init__(self, openai_api_key: str):
        """
        Inicializar servicio RAG

        Args:
            openai_api_key: API key de OpenAI
        """
        self.openai_api_key = openai_api_key
        self.base_url = "https://api.openai.com/v1"
        self.embedding_model = "text-embedding-ada-002"  # Modelo de embeddings de OpenAI
        self.embedding_dimension = 1536  # Dimensión del vector para ada-002

    async def generar_embedding(self, texto: str) -> List[float]:
        """
        Generar embedding para un texto

        Args:
            texto: Texto a convertir en embedding

        Returns:
            Lista de números flotantes (vector embedding)
        """
        try:
            # Limpiar y truncar texto si es muy largo (límite de OpenAI: 8191 tokens)
            texto_limpio = texto.strip()
            if len(texto_limpio) > 8000:  # Aproximadamente 8000 caracteres
                texto_limpio = texto_limpio[:8000]

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.embedding_model,
                        "input": texto_limpio,
                    },
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error generando embedding: {error_msg}")
                    raise Exception(f"Error generando embedding: {error_msg}")

                data = response.json()
                embedding = data["data"][0]["embedding"]

                return embedding

        except Exception as e:
            logger.error(f"Error generando embedding: {e}", exc_info=True)
            raise

    async def generar_embeddings_batch(self, textos: List[str]) -> List[List[float]]:
        """
        Generar embeddings para múltiples textos (más eficiente)

        Args:
            textos: Lista de textos

        Returns:
            Lista de embeddings
        """
        try:
            # Limpiar textos
            textos_limpios = [t.strip()[:8000] for t in textos]

            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.openai_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.embedding_model,
                        "input": textos_limpios,
                    },
                )

                if response.status_code != 200:
                    error_msg = response.text
                    logger.error(f"Error generando embeddings batch: {error_msg}")
                    raise Exception(f"Error generando embeddings: {error_msg}")

                data = response.json()
                embeddings = [item["embedding"] for item in data["data"]]

                return embeddings

        except Exception as e:
            logger.error(f"Error generando embeddings batch: {e}", exc_info=True)
            raise

    def calcular_similitud_coseno(
        self, embedding1: List[float], embedding2: List[float]
    ) -> float:
        """
        Calcular similitud coseno entre dos embeddings

        Args:
            embedding1: Primer embedding
            embedding2: Segundo embedding

        Returns:
            Similitud coseno (0-1)
        """
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calcular similitud coseno
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)
            return float(similarity)

        except Exception as e:
            logger.error(f"Error calculando similitud: {e}", exc_info=True)
            return 0.0

    def buscar_documentos_relevantes(
        self,
        query_embedding: List[float],
        documento_embeddings: List[Dict],
        top_k: int = 3,
        umbral_similitud: float = 0.7,
    ) -> List[Dict]:
        """
        Buscar documentos más relevantes usando similitud coseno

        Args:
            query_embedding: Embedding de la consulta
            documento_embeddings: Lista de dicts con 'embedding' y 'documento_id'
            top_k: Número de documentos a retornar
            umbral_similitud: Umbral mínimo de similitud

        Returns:
            Lista de documentos ordenados por similitud
        """
        try:
            resultados = []

            for doc in documento_embeddings:
                embedding = doc.get("embedding")
                if not embedding:
                    continue

                similitud = self.calcular_similitud_coseno(query_embedding, embedding)

                if similitud >= umbral_similitud:
                    resultados.append(
                        {
                            "documento_id": doc.get("documento_id"),
                            "chunk_index": doc.get("chunk_index", 0),
                            "texto_chunk": doc.get("texto_chunk"),
                            "similitud": similitud,
                        }
                    )

            # Ordenar por similitud descendente
            resultados.sort(key=lambda x: x["similitud"], reverse=True)

            # Retornar top_k
            return resultados[:top_k]

        except Exception as e:
            logger.error(f"Error buscando documentos relevantes: {e}", exc_info=True)
            return []

    def dividir_texto_en_chunks(
        self, texto: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[str]:
        """
        Dividir texto en chunks para procesamiento

        Args:
            texto: Texto a dividir
            chunk_size: Tamaño de cada chunk
            overlap: Solapamiento entre chunks

        Returns:
            Lista de chunks
        """
        if len(texto) <= chunk_size:
            return [texto]

        chunks = []
        start = 0

        while start < len(texto):
            end = start + chunk_size
            chunk = texto[start:end]

            # Intentar cortar en un punto natural (espacio, punto, etc.)
            if end < len(texto):
                # Buscar último espacio o punto
                for i in range(len(chunk) - 1, max(0, len(chunk) - 100), -1):
                    if chunk[i] in [" ", ".", "\n", "!", "?"]:
                        chunk = chunk[: i + 1]
                        end = start + len(chunk)
                        break

            chunks.append(chunk.strip())
            start = end - overlap  # Solapamiento

        return chunks

