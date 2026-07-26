"""
ShaddAI · ingesta universal de archivos.
Detecta el tipo y devuelve o bien una tabla (DataFrame) o bien texto plano,
para que ShaddAI pueda razonar sobre CUALQUIER archivo.
"""
import io
import json
import pandas as pd

# Extensiones que se tratan como datos tabulares (→ gráficos + stats)
EXT_TABLA = {".csv", ".tsv", ".xlsx", ".xls", ".json"}
# Extensiones que se tratan como texto/documento (→ ShaddAI lee y razona)
EXT_TEXTO = {".txt", ".md", ".pdf", ".py", ".js", ".ts", ".java", ".sql",
             ".log", ".html", ".css", ".xml", ".yaml", ".yml", ".sh"}


def detectar_tipo(nombre: str) -> str:
    """Devuelve 'tabla', 'texto' o 'desconocido' según la extensión."""
    ext = _ext(nombre)
    if ext in EXT_TABLA:
        return "tabla"
    if ext in EXT_TEXTO:
        return "texto"
    return "desconocido"


def _ext(nombre: str) -> str:
    return ("." + nombre.rsplit(".", 1)[-1].lower()) if "." in nombre else ""


def leer_tabla(nombre: str, contenido: bytes) -> pd.DataFrame:
    """Lee un archivo tabular a DataFrame según su extensión."""
    ext = _ext(nombre)
    buffer = io.BytesIO(contenido)
    if ext == ".csv":
        return pd.read_csv(buffer)
    if ext == ".tsv":
        return pd.read_csv(buffer, sep="\t")
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(buffer)
    if ext == ".json":
        data = json.loads(contenido.decode("utf-8", errors="ignore"))
        # Si es lista de objetos → tabla; si es dict → normalizar
        return pd.json_normalize(data)
    raise ValueError(f"Extensión de tabla no soportada: {ext}")


def leer_texto(nombre: str, contenido: bytes) -> str:
    """Extrae texto plano de un archivo de documento/código."""
    ext = _ext(nombre)
    if ext == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(contenido))
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    # Cualquier otro: decodificar como texto
    return contenido.decode("utf-8", errors="ignore")
