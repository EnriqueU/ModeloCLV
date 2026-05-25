"""
API REST del modelo CLV construida con FastAPI.
"""
from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from clv.schemas import LoteInput, LoteOutput, OperacionInput, OperacionOutput
from clv.wrapper import CLVWrapper

_DATA_DIR = Path(os.getenv("CLV_DATA_DIR", str(Path(__file__).parent.parent.parent / "data")))

app = FastAPI(
    title="CLV Model API",
    description=(
        "Servicio REST para calcular el Customer Lifetime Value (CLV) "
        "y encontrar la TEA óptima dado un ROA target. "
        "Soporta cálculo unitario y por lote."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    contact={"name": "Equipo de Modelos", "email": "modelos@bcp.com.pe"},
)

_wrapper: CLVWrapper | None = None


def _get_wrapper() -> CLVWrapper:
    """Retorna la instancia única del wrapper, creándola si no existe."""
    global _wrapper
    if _wrapper is None:
        _wrapper = CLVWrapper(_DATA_DIR)
    return _wrapper


# ---------------------------------------------------------------------------
# Manejador global de excepciones no controladas
# ---------------------------------------------------------------------------

@app.exception_handler(Exception)
async def _handler_general(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detalle": str(exc),
            "endpoint": str(request.url),
        },
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get(
    "/health",
    tags=["Salud"],
    summary="Verifica que el servicio esté activo",
)
def health() -> dict[str, Any]:
    """Confirma que la API está corriendo y los datos están cargados"""
    try:
        w = _get_wrapper()
        return {
            "status": "ok",
            "data_dir": str(_DATA_DIR),
            "productos_disponibles": sorted(w._loader.costos["producto"].unique().tolist()),
            "monedas_disponibles": sorted(w._loader.costos["moneda"].unique().tolist()),
        }
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"No se pudieron cargar los archivos de datos: {exc}",
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post(
    "/calcular",
    tags=["CLV"],
    summary="Calcula la TEA óptima y el CLV para una operación",
)
def calcular(operacion: OperacionInput) -> dict[str, Any]:
    """Recibe los parámetros de una operación y devuelve la TEA óptima"""
    try:
        wrapper = _get_wrapper()
        t0 = time.perf_counter()
        output, df_curva = wrapper.procesar_operacion(operacion)
        elapsed = round(time.perf_counter() - t0, 4)

        return {
            **output.model_dump(),
            "tiempo_segundos": elapsed,
            "curvas": df_curva.to_dict(orient="records"),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Parámetros inválidos: {exc}")
    except KeyError as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Combinación producto/moneda no encontrada: {exc}",
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post(
    "/calcular/lote",
    response_model=LoteOutput,
    tags=["CLV"],
    summary="Procesa múltiples operaciones en una sola llamada",
)
def calcular_lote(lote: LoteInput) -> LoteOutput:
    """Calcula la TEA óptima para un lote de operaciones"""
    try:
        wrapper = _get_wrapper()
        resultados: list[OperacionOutput] = []
        for op in lote.operaciones:
            output, _ = wrapper.procesar_operacion(op)
            resultados.append(output)
        return LoteOutput(resultados=resultados, total_procesadas=len(resultados))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Error en alguna operación: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
