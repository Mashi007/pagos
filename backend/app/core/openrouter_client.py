"""
Cliente HTTP para OpenRouter (chat completions).
Usado por configuracion_ai y por el servicio de respuesta IA para imágenes de cobranza.
No accede a BD; recibe api_key y model como parámetros.
"""
import json
import urllib.request
import urllib.error
from typing import Iterator, Optional

OPENROUTER_TIMEOUT = 45


def call_openrouter(
    messages: list[dict],
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> dict:
    """
    Llama a OpenRouter API. Devuelve el JSON de respuesta.
    Lanza urllib.error.HTTPError o otros Exception en error.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://rapicredit.onrender.com",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=OPENROUTER_TIMEOUT) as resp:
        return json.loads(resp.read().decode())


def call_openrouter_stream(
    messages: list[dict],
    api_key: str,
    model: str,
    temperature: float = 0.7,
    max_tokens: int = 500,
) -> Iterator[str]:
    """
    Llama a OpenRouter API con streaming. Genera chunks de contenido.
    Usa httpx para lectura por chunks (más limpio que urllib para SSE).
    """
    import httpx

    url = "https://openrouter.ai/api/v1/chat/completions"
    body = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://rapicredit.onrender.com",
    }
    with httpx.Client(timeout=OPENROUTER_TIMEOUT) as client:
        with client.stream("POST", url, json=body, headers=headers) as resp:
            resp.raise_for_status()
            buffer = ""
            for chunk in resp.iter_text():
                buffer += chunk
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            return
                        try:
                            obj = json.loads(data)
                            content = (obj.get("choices") or [{}])[0].get("delta", {}).get("content")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            pass
