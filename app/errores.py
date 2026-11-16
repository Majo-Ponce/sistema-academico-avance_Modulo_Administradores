"""Manejo centralizado de las respuestas de error de la API.

Todas las respuestas de error comparten el mismo formato:

    {
        "detail":  ...,               # se conserva tal cual (lo usa el frontend)
        "mensaje": "texto legible",   # siempre un texto en español
        "codigo":  "NO_ENCONTRADO",   # código estable para el frontend
        "estado":  404,               # código HTTP
        "ruta":    "/api/v1/...",
        "metodo":  "GET",
        "fecha":   "2026-11-15T10:00:00+00:00"
    }

Los errores de validación (422) agregan "errores": [{campo, mensaje, tipo}]
y los errores internos (500) agregan "id_error" para rastrearlos en el log.
"""

import logging
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("api.errores")

# Mejora 1: código estable por cada estado HTTP.
CODIGOS_POR_ESTADO = {
    400: "SOLICITUD_INVALIDA",
    401: "NO_AUTENTICADO",
    403: "ACCESO_DENEGADO",
    404: "NO_ENCONTRADO",
    405: "METODO_NO_PERMITIDO",
    409: "CONFLICTO",
    422: "DATOS_INVALIDOS",
    429: "DEMASIADAS_SOLICITUDES",
    500: "ERROR_INTERNO",
}

# Mejora 5: traducción de los mensajes en inglés que genera el framework.
TRADUCCIONES_FRAMEWORK = {
    "Not Found": "La ruta o el recurso solicitado no existe",
    "Method Not Allowed": "El método HTTP no está permitido en esta ruta",
    "Not authenticated": "Debe iniciar sesión para acceder a este recurso",
    "Unauthorized": "No autorizado",
    "Forbidden": "Acceso denegado",
    "Bad Request": "Solicitud inválida",
    "Internal Server Error": "Error interno del servidor",
}

# Mejora 2: mensajes en español para los errores de validación más comunes.
MENSAJES_VALIDACION = {
    "missing": "Este campo es obligatorio",
    "string_too_short": "Debe tener al menos {min_length} caracteres",
    "string_too_long": "Debe tener como máximo {max_length} caracteres",
    "string_type": "Debe ser un texto",
    "string_pattern_mismatch": "El formato no es válido",
    "int_parsing": "Debe ser un número entero",
    "int_type": "Debe ser un número entero",
    "float_parsing": "Debe ser un número",
    "float_type": "Debe ser un número",
    "bool_parsing": "Debe ser verdadero o falso",
    "greater_than": "Debe ser mayor que {gt}",
    "greater_than_equal": "Debe ser mayor o igual que {ge}",
    "less_than": "Debe ser menor que {lt}",
    "less_than_equal": "Debe ser menor o igual que {le}",
    "date_parsing": "Debe ser una fecha válida (AAAA-MM-DD)",
    "date_from_datetime_parsing": "Debe ser una fecha válida (AAAA-MM-DD)",
    "time_parsing": "Debe ser una hora válida (HH:MM)",
    "literal_error": "Debe ser uno de: {expected}",
    "enum": "Debe ser uno de: {expected}",
    "json_invalid": "El cuerpo de la solicitud no es un JSON válido",
    "model_attributes_type": "El cuerpo de la solicitud debe ser un objeto JSON",
    "dict_type": "Debe ser un objeto JSON",
    "list_type": "Debe ser una lista",
    "extra_forbidden": "Este campo no está permitido",
}


def _cuerpo_error(
    request: Request,
    estado: int,
    mensaje: str,
    detail: Any = None,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "detail": mensaje if detail is None else detail,
        "mensaje": mensaje,
        "codigo": CODIGOS_POR_ESTADO.get(estado, f"ERROR_{estado}"),
        "estado": estado,
        "ruta": request.url.path,
        "metodo": request.method,
        "fecha": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **extra,
    }


def _traducir_error_validacion(error: dict[str, Any]) -> dict[str, str]:
    # "loc" llega como ("body", "correo"); se quita el origen para dejar el campo.
    ubicacion = [str(parte) for parte in error.get("loc", ()) if parte not in ("body", "query", "path")]
    campo = ".".join(ubicacion) or "solicitud"
    tipo = error.get("type", "")
    plantilla = MENSAJES_VALIDACION.get(tipo)

    if plantilla:
        try:
            mensaje = plantilla.format(**(error.get("ctx") or {}))
        except (KeyError, IndexError):
            mensaje = plantilla
    else:
        # Los validadores propios (field_validator) ya escriben en español;
        # Pydantic les antepone "Value error, ", que se quita.
        mensaje = str(error.get("msg", "Valor no válido")).removeprefix("Value error, ")

    return {"campo": campo, "mensaje": mensaje, "tipo": tipo}


async def manejar_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, str):
        detail = TRADUCCIONES_FRAMEWORK.get(detail, detail)
        mensaje = detail
    else:
        mensaje = TRADUCCIONES_FRAMEWORK.get(str(detail), "Ocurrió un error en la solicitud")
    return JSONResponse(
        status_code=exc.status_code,
        content=_cuerpo_error(request, exc.status_code, mensaje, detail),
        headers=getattr(exc, "headers", None),
    )


async def manejar_validacion(request: Request, exc: RequestValidationError) -> JSONResponse:
    errores = [_traducir_error_validacion(error) for error in exc.errors()]
    resumen = "; ".join(f"{e['campo']}: {e['mensaje']}" for e in errores)
    # "detail" conserva la lista original de Pydantic porque el frontend la
    # usa para marcar en rojo los campos inválidos.
    return JSONResponse(
        status_code=422,
        content=_cuerpo_error(
            request,
            422,
            f"Revise los datos enviados. {resumen}",
            detail=_serializable(exc.errors()),
            errores=errores,
        ),
    )


async def manejar_integridad(request: Request, exc: sqlite3.IntegrityError) -> JSONResponse:
    # Mejora 3: una restricción de la base de datos que no se capturó en el
    # router ya no termina en 500, sino en un 409 explicado.
    texto = str(exc)
    if "UNIQUE" in texto:
        mensaje = "Ya existe un registro con esos datos (valor duplicado)"
    elif "FOREIGN KEY" in texto:
        mensaje = "El registro está relacionado con otros datos que no existen o que lo usan"
    elif "NOT NULL" in texto:
        mensaje = "Falta un dato obligatorio"
    elif "CHECK" in texto:
        mensaje = "Uno de los valores no cumple las reglas permitidas"
    else:
        mensaje = "La operación viola una restricción de la base de datos"
    logger.warning("IntegrityError en %s %s: %s", request.method, request.url.path, texto)
    return JSONResponse(status_code=409, content=_cuerpo_error(request, 409, mensaje))


async def manejar_inesperado(request: Request, exc: Exception) -> JSONResponse:
    # Mejora 4: el cliente nunca ve la traza; recibe un id para reportarlo y
    # el detalle completo queda en el log del servidor.
    id_error = uuid.uuid4().hex[:8]
    logger.exception("Error %s en %s %s", id_error, request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content=_cuerpo_error(
            request,
            500,
            f"Ocurrió un error inesperado en el servidor. Reporte este código: {id_error}",
            id_error=id_error,
        ),
    )


def _serializable(errores: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # "ctx" puede traer objetos (p. ej. la excepción original) que no son JSON.
    limpios = []
    for error in errores:
        copia = {k: v for k, v in error.items() if k not in ("ctx", "url")}
        if "ctx" in error:
            copia["ctx"] = {k: str(v) for k, v in error["ctx"].items()}
        limpios.append(copia)
    return limpios


def registrar_manejadores_error(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, manejar_http)
    app.add_exception_handler(RequestValidationError, manejar_validacion)
    app.add_exception_handler(sqlite3.IntegrityError, manejar_integridad)
    app.add_exception_handler(Exception, manejar_inesperado)
