"""
ShaddAI · inspector de seguridad (defensivo).
Analiza los encabezados de seguridad HTTP de un sitio web y reporta
qué buenas prácticas faltan. Uso legítimo: revisar sitios propios o
con autorización. NO realiza explotación ni escaneo intrusivo.
"""
import requests

# Encabezados de seguridad recomendados y para qué sirven.
HEADERS_RECOMENDADOS = {
    "strict-transport-security": "Fuerza HTTPS (evita downgrade a HTTP).",
    "content-security-policy": "Mitiga XSS controlando qué recursos cargan.",
    "x-frame-options": "Evita clickjacking (que te embeban en un iframe).",
    "x-content-type-options": "Evita MIME sniffing (nosniff).",
    "referrer-policy": "Controla qué info de referrer se filtra.",
    "permissions-policy": "Limita APIs del navegador (cámara, micrófono, etc.).",
}


def inspeccionar(url: str) -> dict:
    """Hace una petición GET y evalúa los encabezados de seguridad."""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    try:
        resp = requests.get(url, timeout=15, allow_redirects=True)
    except requests.exceptions.SSLError:
        return {"error": "Fallo de certificado SSL/TLS.", "url": url}
    except requests.exceptions.ConnectionError:
        return {"error": "No se pudo conectar con el sitio.", "url": url}
    except Exception as e:
        return {"error": f"Error al inspeccionar: {e}", "url": url}

    headers = {k.lower(): v for k, v in resp.headers.items()}

    presentes, faltantes = [], []
    for h, desc in HEADERS_RECOMENDADOS.items():
        if h in headers:
            presentes.append({"header": h, "valor": headers[h], "descripcion": desc})
        else:
            faltantes.append({"header": h, "descripcion": desc})

    # Puntaje simple: % de encabezados presentes
    total = len(HEADERS_RECOMENDADOS)
    puntaje = round(len(presentes) / total * 100)

    # Señales adicionales
    usa_https = url.startswith("https://") and not resp.url.startswith("http://")
    server = headers.get("server")

    return {
        "url": resp.url,
        "status": resp.status_code,
        "usa_https": usa_https,
        "servidor_expuesto": server,  # exponer versión del server es info leak
        "puntaje": puntaje,
        "headers_presentes": presentes,
        "headers_faltantes": faltantes,
    }
