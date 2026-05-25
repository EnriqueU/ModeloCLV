"""
Esquemas de validación para la API REST.
"""
from __future__ import annotations

try:
    from pydantic import BaseModel, Field, field_validator

    class OperacionInput(BaseModel):
        """Parámetros de entrada para una operación a calcular.

        Attributes:
            id_operacion: identificador libre, se devuelve en el resultado.
            producto: tipo de producto financiero.
            moneda: moneda de la operación.
            monto: capital a desembolsar en unidades monetarias.
            plazo_meses: duración del crédito en meses.
            roa_target: retorno sobre activos objetivo (fracción, no porcentaje).
        """

        id_operacion: str = Field(default="", description="ID de la operación")
        producto: str = Field(..., description="Credito | Leasing | Tarjeta")
        moneda: str = Field(..., description="PEN | USD")
        monto: float = Field(..., gt=0, description="Monto desembolsado")
        plazo_meses: int = Field(..., gt=0, le=360, description="Plazo en meses")
        roa_target: float = Field(..., gt=0, lt=1.0, description="ROA objetivo")

        @field_validator("producto")
        @classmethod
        def _producto_valido(cls, v: str) -> str:
            opciones = {"Credito", "Leasing", "Tarjeta"}
            if v not in opciones:
                raise ValueError(f"'{v}' no es válido. Opciones: {opciones}")
            return v

        @field_validator("moneda")
        @classmethod
        def _moneda_valida(cls, v: str) -> str:
            opciones = {"PEN", "USD"}
            if v not in opciones:
                raise ValueError(f"'{v}' no es válida. Opciones: {opciones}")
            return v

    class OperacionOutput(BaseModel):
        """Resultado del cálculo para una operación.

        Attributes:
            tea: tasa efectiva anual óptima encontrada.
            clv_unitario: CLV como fracción del monto (debería ≈ roa_target).
            error_optimizacion: diferencia absoluta entre CLV y roa_target.
        """

        id_operacion: str
        producto: str
        moneda: str
        monto: float
        plazo_meses: int
        roa_target: float
        tea: float
        clv_unitario: float
        error_optimizacion: float

    class LoteInput(BaseModel):
        """Lista de operaciones para el endpoint de procesamiento por lote."""

        operaciones: list[OperacionInput] = Field(..., min_length=1)

    class LoteOutput(BaseModel):
        """Resultado del procesamiento de un lote de operaciones."""

        resultados: list[OperacionOutput]
        total_procesadas: int

    PYDANTIC_DISPONIBLE = True

except ModuleNotFoundError:
    from dataclasses import dataclass, field as dc_field

    PYDANTIC_DISPONIBLE = False

    @dataclass
    class OperacionInput:  # type: ignore[no-redef]
        producto: str
        moneda: str
        monto: float
        plazo_meses: int
        roa_target: float
        id_operacion: str = ""

        def model_dump(self) -> dict:
            return self.__dict__.copy()

    @dataclass
    class OperacionOutput:  # type: ignore[no-redef]
        id_operacion: str
        producto: str
        moneda: str
        monto: float
        plazo_meses: int
        roa_target: float
        tea: float
        clv_unitario: float
        error_optimizacion: float

        def model_dump(self) -> dict:
            return self.__dict__.copy()

    @dataclass
    class LoteInput:  # type: ignore[no-redef]
        operaciones: list

    @dataclass
    class LoteOutput:  # type: ignore[no-redef]
        resultados: list
        total_procesadas: int
