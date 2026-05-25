"""
Curvas de tasa de fondeo por producto, moneda y plazo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class TasaCurva:
    """Interpola tasas de fondeo desde curvas por producto y moneda.

    Args:
        df: DataFrame con columnas producto, moneda, plazo_dias
            y tasa_anual, ordenable por plazo_dias.
    """

    _TASA_FALLBACK: float = 0.05  # si no hay datos para el producto/moneda

    def __init__(self, df: pd.DataFrame) -> None:
        self._curvas: dict[tuple[str, str], tuple[np.ndarray, np.ndarray]] = {}
        for (prod, mon), grupo in df.groupby(["producto", "moneda"]):
            ordenado = grupo.sort_values("plazo_dias")
            self._curvas[(str(prod), str(mon))] = (
                ordenado["plazo_dias"].to_numpy(dtype=float),
                ordenado["tasa_anual"].to_numpy(dtype=float),
            )

    def tasa_en_plazo(self, producto: str, moneda: str, plazo_dias: float) -> float:
        """Retorna la tasa anual de fondeo interpolada para el plazo dado.

        Args:
            producto: tipo de producto financiero.
            moneda: PEN o USD.
            plazo_dias: plazo en días (ej: mes 3 = 90 días).

        Returns:
            Tasa anual como fracción (ej: 0.062 = 6.2% anual).
        """
        clave = (producto, moneda)
        if clave not in self._curvas:
            return self._TASA_FALLBACK
        plazos, tasas = self._curvas[clave]
        return float(np.interp(plazo_dias, plazos, tasas))

    def obtener_tasa_interpolada(
        self, producto: str, moneda: str, plazo_dias: float
    ) -> float:
        return self.tasa_en_plazo(producto, moneda, plazo_dias)
