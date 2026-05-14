# app/main.py
#
# Punto de entrada de la aplicacion FastAPI.
# Define las rutas, el scheduler de actualizacion automatica,
# y sirve el frontend estatico.

import asyncio
import os
from contextlib import asynccontextmanager
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

from app.fetchers.cve_fetcher import fetch_critical_cves
from app.fetchers.news_fetcher import fetch_news

load_dotenv()

# ------------------------------------------------------------------------------
# Cache en memoria: almacena los datos entre requests sin base de datos
# En produccion podrias reemplazar esto con Redis
# ------------------------------------------------------------------------------
cache = {
    "cves": [],
    "news": [],
    "last_updated": None,
}


async def refresh_data():
    """
    Funcion que actualiza el cache consultando NVD y los feeds RSS.
    Se ejecuta al arrancar y cada REFRESH_INTERVAL minutos.
    """
    print(f"[Scheduler] Actualizando datos... {datetime.now().strftime('%H:%M:%S')}")
    days_back = int(os.getenv("CVE_DAYS_BACK", 7))

    # Ejecutamos ambas consultas en paralelo para mayor velocidad
    cves, news = await asyncio.gather(
        fetch_critical_cves(days_back=days_back),
        fetch_news(),
        return_exceptions=True,
    )

    if not isinstance(cves, Exception):
        cache["cves"] = cves
    if not isinstance(news, Exception):
        cache["news"] = news

    cache["last_updated"] = datetime.now().strftime("%d/%m/%Y %H:%M UTC")
    print(f"[Scheduler] Listo. CVEs: {len(cache['cves'])} | Noticias: {len(cache['news'])}")


# ------------------------------------------------------------------------------
# Lifespan: se ejecuta al arrancar y al apagar la app
# Es el reemplazo moderno de @app.on_event("startup")
# ------------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Carga inicial de datos
    await refresh_data()

    # Scheduler: actualiza cada N minutos en background
    interval = int(os.getenv("REFRESH_INTERVAL", 60))
    scheduler = AsyncIOScheduler()
    scheduler.add_job(refresh_data, "interval", minutes=interval)
    scheduler.start()

    yield  # La app corre aqui

    scheduler.shutdown()


# ------------------------------------------------------------------------------
# Instancia de FastAPI
# ------------------------------------------------------------------------------
app = FastAPI(
    title="CyberFeed",
    description="Agregador de noticias de ciberseguridad y CVEs criticos",
    version="1.0.0",
    lifespan=lifespan,
)

# Servir archivos estaticos (CSS, JS)
app.mount("/static", StaticFiles(directory="static"), name="static")


# ------------------------------------------------------------------------------
# Rutas de la API
# ------------------------------------------------------------------------------

@app.get("/api/feed")
async def get_feed(type: str = "all", severity: str = "all", q: str = ""):
    """
    Devuelve el feed combinado de CVEs y noticias.
    Parametros:
      - type: 'all' | 'cve' | 'news'
      - severity: 'all' | 'critical' | 'high'
      - q: termino de busqueda (busca en titulo y descripcion)
    """
    items = []

    if type in ("all", "cve"):
        filtered_cves = cache["cves"]
        if severity != "all":
            filtered_cves = [c for c in filtered_cves if c["severity"] == severity]
        items += filtered_cves

    if type in ("all", "news"):
        items += cache["news"]

    # Filtro de busqueda
    if q:
        q_lower = q.lower()
        items = [
            i for i in items
            if q_lower in i["title"].lower()
            or q_lower in i.get("description", "").lower()
            or q_lower in i.get("summary", "").lower()
            or q_lower in i.get("affected", "").lower()
        ]

    return {
        "items": items,
        "total": len(items),
        "last_updated": cache["last_updated"],
        "stats": {
            "critical": len([c for c in cache["cves"] if c["severity"] == "critical"]),
            "high": len([c for c in cache["cves"] if c["severity"] == "high"]),
            "news": len(cache["news"]),
        },
    }


@app.get("/api/refresh")
async def manual_refresh():
    """Fuerza una actualizacion manual del cache."""
    await refresh_data()
    return {"status": "ok", "last_updated": cache["last_updated"]}


@app.get("/api/stats")
async def get_stats():
    """Devuelve solo las estadisticas del cache actual."""
    return {
        "critical": len([c for c in cache["cves"] if c["severity"] == "critical"]),
        "high": len([c for c in cache["cves"] if c["severity"] == "high"]),
        "news": len(cache["news"]),
        "last_updated": cache["last_updated"],
    }


# ------------------------------------------------------------------------------
# Ruta principal: sirve el frontend
# ------------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index():
    with open("templates/index.html", "r") as f:
        return f.read()
