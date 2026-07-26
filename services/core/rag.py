"""
ShaddAI · motor de PROYECTOS (RAG).
Sube un proyecto entero (zip), lo indexa por pedazos y permite preguntarle
cualquier cosa: busca los fragmentos relevantes y se los pasa a la IA.

Todo local y gratis: embeddings con nomic-embed-text (Ollama) + búsqueda
por similitud con numpy. Sin bases vectoriales externas.
"""
import os
import io
import json
import zipfile
import numpy as np
import requests

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

INDEX_DIR = os.path.join(os.path.dirname(__file__), "rag_index")
os.makedirs(INDEX_DIR, exist_ok=True)
REGISTRO = os.path.join(INDEX_DIR, "proyectos.json")

# Extensiones de texto/código que sí se indexan
TEXT_EXT = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".sql", ".html", ".css",
    ".scss", ".sass", ".md", ".txt", ".json", ".yaml", ".yml", ".sh", ".xml",
    ".c", ".cpp", ".h", ".hpp", ".go", ".rb", ".php", ".cs", ".vue", ".kt",
    ".rs", ".swift", ".dart", ".r", ".ini", ".cfg", ".toml", ".env.example",
}
# Carpetas que se ignoran (ruido)
SKIP_DIRS = {"node_modules", ".git", "venv", ".venv", "dist", "build",
             "__pycache__", ".vite", "target", ".idea", ".vscode", "coverage"}

MAX_CHUNKS = 1200          # tope para que el indexado no eterno en CPU
CHUNK_SIZE = 900           # caracteres por fragmento
CHUNK_OVERLAP = 120


# ---------- utilidades ----------
def _cargar_registro() -> dict:
    if os.path.exists(REGISTRO):
        with open(REGISTRO, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _guardar_registro(reg: dict):
    with open(REGISTRO, "w", encoding="utf-8") as f:
        json.dump(reg, f, ensure_ascii=False, indent=2)


def _embed(texto: str) -> list:
    """Devuelve el vector embedding de un texto (Ollama)."""
    resp = requests.post(
        f"{OLLAMA_URL}/api/embeddings",
        json={"model": EMBED_MODEL, "prompt": texto},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def _trocear(texto: str) -> list:
    """Parte un texto en fragmentos con solapamiento."""
    chunks = []
    i = 0
    while i < len(texto):
        chunks.append(texto[i:i + CHUNK_SIZE])
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


def _es_texto(nombre: str) -> bool:
    n = nombre.lower()
    if n.endswith(".env.example"):
        return True
    ext = os.path.splitext(n)[1]
    return ext in TEXT_EXT


# ---------- indexado ----------
def indexar_zip(contenido: bytes, nombre_proyecto: str) -> dict:
    """Descomprime un zip, indexa sus archivos de texto/código y guarda el índice."""
    reg = _cargar_registro()
    nuevo_id = str(max([int(k) for k in reg.keys()], default=0) + 1)

    fragmentos = []   # {"archivo": ..., "texto": ...}
    archivos_ok = 0

    with zipfile.ZipFile(io.BytesIO(contenido)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            partes = info.filename.split("/")
            if any(p in SKIP_DIRS for p in partes):
                continue
            if not _es_texto(info.filename):
                continue
            if info.file_size > 400_000:   # saltar archivos enormes
                continue
            try:
                texto = z.read(info).decode("utf-8", errors="ignore")
            except Exception:
                continue
            if not texto.strip():
                continue
            archivos_ok += 1
            for trozo in _trocear(texto):
                fragmentos.append({"archivo": info.filename, "texto": trozo})
                if len(fragmentos) >= MAX_CHUNKS:
                    break
            if len(fragmentos) >= MAX_CHUNKS:
                break

    if not fragmentos:
        raise ValueError("El zip no contiene archivos de texto/código indexables.")

    # Embeddings de cada fragmento
    vectores = []
    textos_ok = []
    for fr in fragmentos:
        try:
            vectores.append(_embed(fr["texto"]))
            textos_ok.append(fr)
        except Exception:
            continue

    emb = np.array(vectores, dtype=np.float32)
    np.save(os.path.join(INDEX_DIR, f"{nuevo_id}_emb.npy"), emb)
    with open(os.path.join(INDEX_DIR, f"{nuevo_id}_chunks.json"), "w", encoding="utf-8") as f:
        json.dump(textos_ok, f, ensure_ascii=False)

    reg[nuevo_id] = {
        "id": nuevo_id,
        "nombre": nombre_proyecto,
        "archivos": archivos_ok,
        "fragmentos": len(textos_ok),
    }
    _guardar_registro(reg)
    return reg[nuevo_id]


def listar_proyectos() -> list:
    return list(_cargar_registro().values())


# ---------- búsqueda ----------
def buscar_fragmentos(proyecto_id: str, pregunta: str, k: int = 6) -> list:
    """Devuelve los k fragmentos más relevantes a la pregunta."""
    ruta_emb = os.path.join(INDEX_DIR, f"{proyecto_id}_emb.npy")
    ruta_ch = os.path.join(INDEX_DIR, f"{proyecto_id}_chunks.json")
    if not (os.path.exists(ruta_emb) and os.path.exists(ruta_ch)):
        return []

    emb = np.load(ruta_emb)
    with open(ruta_ch, encoding="utf-8") as f:
        chunks = json.load(f)

    q = np.array(_embed(pregunta), dtype=np.float32)
    # Similitud coseno
    emb_norm = emb / (np.linalg.norm(emb, axis=1, keepdims=True) + 1e-9)
    q_norm = q / (np.linalg.norm(q) + 1e-9)
    sims = emb_norm @ q_norm
    top = np.argsort(sims)[::-1][:k]
    return [chunks[i] for i in top]
