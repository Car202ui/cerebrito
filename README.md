# 🧠 cerebrito

Plataforma versátil de análisis, inspección de seguridad y base de conocimiento.
Arquitectura de **microservicios** — cada capacidad es un servicio independiente.

## Visión

Un núcleo que permite:
- Subir datos (CSV) y analizarlos
- Guardar y consultar una base de conocimiento de proyectos
- Inspección de seguridad / pruebas de vulnerabilidad
- Conexión con IA local (Ollama)
- Informes analíticos (Metabase / exportable a Power BI)
- Mapas de calor de uso

## Arquitectura

```
┌──────────┐      ┌─────────────┐      ┌──────────────┐
│ Frontend │ ───► │   Gateway   │ ───► │  Servicios   │
│  React   │      │  (FastAPI)  │      │  core, ...   │
└──────────┘      └─────────────┘      └──────┬───────┘
                                              │
                                        ┌─────▼─────┐
                                        │   MySQL   │
                                        └───────────┘
```

| Componente | Tecnología | Puerto |
|------------|-----------|--------|
| frontend | React + Vite | 5173 |
| gateway | Python / FastAPI | 8000 |
| services/core | Python / FastAPI | 8001 |
| services/analytics | Python / Pandas / FastAPI | 8002 |
| MySQL | MySQL 8 | 3306 |

## Stack (100% gratis / open-source)

- **Frontend:** React + Vite
- **Backend:** Python + FastAPI (uno por servicio)
- **Base de datos:** MySQL
- **Orquestación:** Docker Compose
- **IA local:** Ollama
- **BI:** Metabase (gratis, self-hosted)

## Requisitos

- Node 20+ ✅
- Python 3.12+
- Docker Desktop
- MySQL 8

## Cómo correr (una vez instalado todo)

```bash
docker compose up --build
```

## Estado

🚧 En desarrollo — Fase 1: núcleo (base de conocimiento + ingesta CSV).
