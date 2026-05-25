"""
Gestión de costos por producto y moneda.
"""
from __future__ import annotations

import pandas as pd


class CostoHandler:
    """Consulta costos de originación y mantenimiento por producto/moneda.

    Args:
        df: DataFrame con columnas producto, moneda,
            costo_originacion_pct y costo_mantenimiento_anual_pct.
    """
    _FALLBACK_ORIG: float = 0.02
    _FALLBACK_MANT: float = 0.02

    def __init__(self, df: pd.DataFrame) -> None:
        self._indice: dict[tuple[str, str], tuple[float, float]] = {}
        for _, fila in df.iterrows():
            clave = (str(fila["producto"]), str(fila["moneda"]))
            self._indice[clave] = (
                float(fila["costo_originacion_pct"]),
                float(fila["costo_mantenimiento_anual_pct"]),
            )

    def costo_originacion(self, producto: str, moneda: str) -> float:
        """Retorna el porcentaje de originación sobre el monto desembolsado.

        Args:
            producto: tipo de producto (Credito, Leasing, Tarjeta).
            moneda: moneda de la operación (PEN, USD).

        Returns:
            Costo como fracción del monto (ej: 0.02 = 2%).
        """
        return self._indice.get((producto, moneda), (self._FALLBACK_ORIG, self._FALLBACK_MANT))[0]

    def costo_mantenimiento(self, producto: str, moneda: str) -> float:
        """Retorna el porcentaje de mantenimiento anual sobre saldo vigente.

        Args:
            producto: tipo de producto (Credito, Leasing, Tarjeta).
            moneda: moneda de la operación (PEN, USD).

        Returns:
            Tasa anual como fracción del saldo (ej: 0.02 = 2% anual).
        """
        return self._indice.get((producto, moneda), (self._FALLBACK_ORIG, self._FALLBACK_MANT))[1]
