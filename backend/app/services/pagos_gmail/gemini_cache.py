"""
Caché simple en memoria para validación de comprobantes Gemini.
Usa hash SHA256 del archivo + form_data para evitar re-procesar imágenes duplicadas.
TTL: 24 horas.
"""
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

CACHE_TTL_HOURS = 24
MAX_CACHE_SIZE = 1000


class GeminiComprobanteCacheEntry:
    """Entrada de caché con TTL."""
    
    def __init__(self, result: Dict[str, Any], created_at: datetime):
        self.result = result
        self.created_at = created_at
    
    def is_expired(self) -> bool:
        """Verifica si la entrada expiró."""
        return datetime.now() - self.created_at > timedelta(hours=CACHE_TTL_HOURS)


class GeminiComprobantesCache:
    """Caché en memoria (por proceso) para validación de comprobantes."""
    
    def __init__(self):
        self.cache: Dict[str, GeminiComprobanteCacheEntry] = {}
    
    def _generate_key(self, image_bytes: bytes, form_data: Dict[str, Any]) -> str:
        """Genera clave única: SHA256(imagen) + SHA256(form_data)."""
        img_hash = hashlib.sha256(image_bytes).hexdigest()
        form_json = json.dumps(form_data, sort_keys=True, default=str)
        form_hash = hashlib.sha256(form_json.encode()).hexdigest()
        return f"{img_hash}:{form_hash}"
    
    def get(self, image_bytes: bytes, form_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Obtiene resultado del caché si existe y no expiró."""
        key = self._generate_key(image_bytes, form_data)
        entry = self.cache.get(key)
        
        if entry:
            if entry.is_expired():
                del self.cache[key]
                return None
            return entry.result
        return None
    
    def set(self, image_bytes: bytes, form_data: Dict[str, Any], result: Dict[str, Any]) -> None:
        """Guarda resultado en caché. Limpia si alcanza tamaño máximo."""
        key = self._generate_key(image_bytes, form_data)
        
        if len(self.cache) >= MAX_CACHE_SIZE:
            oldest_key = min(
                self.cache.keys(),
                key=lambda k: self.cache[k].created_at
            )
            del self.cache[oldest_key]
        
        self.cache[key] = GeminiComprobanteCacheEntry(result, datetime.now())
    
    def clear_expired(self) -> int:
        """Limpia entradas expiradas. Retorna cantidad eliminada."""
        expired_keys = [k for k, v in self.cache.items() if v.is_expired()]
        for k in expired_keys:
            del self.cache[k]
        return len(expired_keys)


_gemini_cache = GeminiComprobantesCache()


def get_gemini_cache() -> GeminiComprobantesCache:
    """Obtiene la instancia global de caché."""
    return _gemini_cache


def cache_get(image_bytes: bytes, form_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Helpers para usar el caché."""
    return _gemini_cache.get(image_bytes, form_data)


def cache_set(image_bytes: bytes, form_data: Dict[str, Any], result: Dict[str, Any]) -> None:
    """Guarda en caché."""
    _gemini_cache.set(image_bytes, form_data, result)
