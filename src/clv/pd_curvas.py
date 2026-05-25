"""
Probabilidad de default y curvas de supervivencia.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class PDCurva:
    """Curvas de supervivencia acumulada por producto.

    Args:
        df: DataFrame con columnas producto, mes y pd_marginal,
            con una fila por mes por producto (hasta 36 meses).
    """

    def __init__(self, df: pd.DataFrame) -> None:
        self._supervivencia: dict[str, np.ndarray] = {}
        self._pd_marginal: dict[str, np.ndarray] = {}

        for producto, grupo in df.groupby("producto"):
            ordenado = grupo.sort_values("mes")
            pds = ordenado["pd_marginal"].to_numpy(dtype=float)
            surv = np.concatenate([[1.0], np.cumprod(1.0 - pds)])

            self._supervivencia[str(producto)] = surv
            self._pd_marginal[str(producto)] = pds

    def supervivencia(self, producto: str, mes: int) -> float:
        """Probabilidad de que el cliente siga activo en el mes indicado.

        Args:
            producto: tipo de producto financiero.
            mes: mes de la operación (0 = desembolso, 1 = primer mes, ...).

        Returns:
            Valor entre 0 y 1. Retorna 1.0 si no hay datos para el producto
            o si el mes supera el horizonte disponible.
        """
        arr = self._supervivencia.get(producto)
        if arr is None or mes >= len(arr):
            return 1.0
        return float(arr[mes])

    def pd_mes(self, producto: str, mes: int) -> float:
        """PD marginal del mes indicado (indexado desde 1).

        Args:
            producto: tipo de producto financiero.
            mes: número de mes (1-indexado).

        Returns:
            Probabilidad de default marginal. Retorna 0.0 si no hay datos.
        """
        arr = self._pd_marginal.get(producto)
        if arr is None or mes - 1 >= len(arr):
            return 0.0
        return float(arr[mes - 1])

    # Alias para retrocompatibilidad
    def supervivencia_en_mes(self, producto: str, mes: int) -> float:
        return self.supervivencia(producto, mes)

    def pd_marginal_mes(self, producto: str, mes: int) -> float:
        return self.pd_mes(producto, mes)
