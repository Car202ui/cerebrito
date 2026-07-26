"""
ShaddAI · razonamiento con Ollama (LLM local, gratis).
Toma estadísticas de un dataset y genera conclusiones/recomendaciones,
o responde preguntas del usuario sobre sus datos.
"""
import os
import json
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")


def _chat(prompt: str, num_predict: int = 500) -> str:
    """Envía un prompt a Ollama y devuelve la respuesta en texto.

    - timeout amplio (la IA en CPU es lenta con textos largos).
    - keep_alive: mantiene el modelo cargado en memoria 30 min → la
      2da consulta en adelante es mucho más rápida (evita recargar).
    - num_predict: limita cuánto genera → no se cuelga generando de más.
    """
    try:
        resp = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {"num_predict": num_predict, "temperature": 0.3},
            },
            timeout=600,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return "⚠️ No pude conectar con Ollama. ¿Está corriendo? (revisá la app de Ollama)."
    except requests.exceptions.ReadTimeout:
        return ("⚠️ La IA tardó demasiado (documento muy grande para tu equipo sin "
                "placa de video). Probá con un archivo más chico o preguntá algo puntual.")
    except Exception as e:
        return f"⚠️ Error al razonar: {e}"


def generar_insights(analytics: dict) -> str:
    """Conclusiones y recomendaciones a partir de las estadísticas del dataset."""
    resumen = json.dumps(analytics, ensure_ascii=False, indent=2)
    prompt = f"""Eres ShaddAI, un analista de datos experto. Te doy las estadísticas
de un conjunto de datos. Escribe en español, de forma clara y breve:

1. Las 3 conclusiones más importantes.
2. Una recomendación concreta para tomar decisiones.

No inventes datos que no estén en las estadísticas. Sé directo.

ESTADÍSTICAS:
{resumen}
"""
    return _chat(prompt)


def responder_pregunta(pregunta: str, analytics: dict) -> str:
    """Responde una pregunta del usuario usando las estadísticas del dataset."""
    resumen = json.dumps(analytics, ensure_ascii=False)
    prompt = f"""Eres ShaddAI, un analista de datos. Responde en español la pregunta
del usuario basándote SOLO en estas estadísticas. Si la información no alcanza,
dilo con honestidad.

ESTADÍSTICAS: {resumen}

PREGUNTA: {pregunta}
"""
    return _chat(prompt)


# Los documentos pueden ser largos; recortamos para que la IA en CPU no se
# demore de más. 6000 caracteres ≈ 2-3 páginas, suficiente para un buen resumen.
MAX_TEXTO = 6000


def generar_insights_texto(texto: str) -> str:
    """Conclusiones sobre un documento/código."""
    fragmento = texto[:MAX_TEXTO]
    prompt = f"""Eres ShaddAI, un asistente experto. Analiza el siguiente contenido
de un archivo y escribe en español, breve y claro:

1. De qué trata el archivo (resumen en 2-3 líneas).
2. Los 3 puntos más importantes.
3. Una observación o recomendación útil.

CONTENIDO:
{fragmento}
"""
    return _chat(prompt)


def responder_pregunta_texto(pregunta: str, texto: str) -> str:
    """Responde una pregunta sobre el contenido de un documento/código."""
    fragmento = texto[:MAX_TEXTO]
    prompt = f"""Eres ShaddAI. Responde en español la pregunta del usuario basándote
SOLO en el siguiente contenido. Si no está en el contenido, dilo con honestidad.

CONTENIDO:
{fragmento}

PREGUNTA: {pregunta}
"""
    return _chat(prompt)


def responder_proyecto(pregunta: str, fragmentos: list) -> str:
    """Responde una pregunta sobre un PROYECTO usando los fragmentos relevantes
    que el buscador RAG encontró. Cita los archivos."""
    if not fragmentos:
        return ("No encontré partes del proyecto relacionadas con tu pregunta. "
                "Probá reformularla o ser más específico.")
    contexto = "\n\n".join(
        f"--- Archivo: {f['archivo']} ---\n{f['texto']}" for f in fragmentos
    )
    prompt = f"""Eres ShaddAI, un ingeniero de software experto. Responde en español
la pregunta del usuario sobre su proyecto, basándote SOLO en los fragmentos de
código/archivos que te doy. Menciona los archivos relevantes. Si la información
no está en los fragmentos, dilo con honestidad (no inventes).

FRAGMENTOS DEL PROYECTO:
{contexto}

PREGUNTA: {pregunta}
"""
    return _chat(prompt, num_predict=700)


def analizar_seguridad(reporte: dict) -> str:
    """Explica en lenguaje claro los hallazgos del inspector de seguridad."""
    datos = json.dumps(reporte, ensure_ascii=False, indent=2)
    prompt = f"""Eres ShaddAI, un experto en seguridad web defensiva. Te doy el
resultado de revisar los encabezados de seguridad de un sitio. Escribe en español:

1. Una evaluación general del nivel de seguridad (en 2 líneas).
2. Los riesgos más importantes por los encabezados que faltan.
3. Recomendaciones concretas y priorizadas para mejorar.

Sé claro y práctico. No inventes hallazgos que no estén en los datos.

RESULTADO DE LA INSPECCIÓN:
{datos}
"""
    return _chat(prompt)
