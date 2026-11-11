from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import inicializar_base_datos
from app.dependencies import solo_admin
from app.routers import (
    asignaturas,
    auth,
    aulas,
    administradores,
    calificaciones,
    carreras,
    docentes,
    estudiantes,
    matriculas,
    panel_docente,
    periodos,
    reportes,
    secciones,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    inicializar_base_datos()
    yield


app = FastAPI(
    title="API del Sistema de Gestión Académica",
    description=(
        "Proyecto demostrativo de Programación II con FastAPI, SQLite, "
        "relaciones entre tablas, validaciones y reglas de negocio."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Permite conectar más adelante un frontend creado con Vite/Vue o React.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIJO = "/api/v1"

# Login: público.
app.include_router(auth.router, prefix=PREFIJO)

# Panel del docente: solo rol DOCENTE (la protección está en el router).
app.include_router(panel_docente.router, prefix=PREFIJO)

# Módulos de gestión global: solo rol ADMIN. Un DOCENTE recibe 403.
SOLO_ADMIN = [Depends(solo_admin)]
for modulo in (
    administradores,
    carreras,
    estudiantes,
    docentes,
    asignaturas,
    periodos,
    aulas,
    secciones,
    matriculas,
    calificaciones,
    reportes,
):
    app.include_router(modulo.router, prefix=PREFIJO, dependencies=SOLO_ADMIN)
# Nota: existía un segundo router de autenticación (app/auth.py, basado en
# SQLAlchemy + columnas "email"/"password_hash") montado aquí sin el
# prefijo /api/v1. No coincide con el esquema real de la tabla "usuarios"
# (ver app/database.py), así que quedaba roto (respondía 500 si se
# llamaba) y además duplicaba la ruta /login. Se quitó su registro; el
# login real y funcional es app.routers.auth, incluido arriba con el
# prefijo /api/v1 (POST /api/v1/auth/login).

@app.get("/salud", tags=["Inicio"])
def comprobar_salud():
    return {"estado": "OK"}


# El frontend (login + dashboard) se sirve desde la carpeta "frontend/".
# Se monta al final para que las rutas de la API definidas arriba siempre
# tengan prioridad sobre los archivos estáticos.
CARPETA_FRONTEND = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/", StaticFiles(directory=CARPETA_FRONTEND, html=True), name="frontend")
