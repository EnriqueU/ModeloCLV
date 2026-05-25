"""
Amortización francesa.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


class AmortizacionFrancesa:
    """Cálculo de cuotas y saldos bajo el esquema francés (cuota constante)"""

    @staticmethod
    def cuota(monto: float, tem: float, n: int) -> float:
        """Calcula la cuota mensual constante del crédito.

        Args:
            monto: capital desembolsado.
            tem: tasa efectiva mensual (ej: 0.015 = 1.5% mensual).
            n: plazo en meses.

        Returns:
            Cuota mensual que el cliente paga todos los meses.
            Si tem <= 0, retorna monto/n (cuota plana sin interés).
        """
        if tem <= 0.0:
            return monto / n
        factor = (1.0 + tem) ** n
        return monto * tem * factor / (factor - 1.0)

    @staticmethod
    def saldo_en_mes(monto: float, tem: float, n: int, t: int) -> float:
        """Saldo pendiente al inicio del mes t (antes de pagar ese mes).

        Args:
            monto: capital desembolsado.
            tem: tasa efectiva mensual.
            n: plazo total en meses.
            t: mes consultado (0 = desembolso, n = último mes).

        Returns:
            Saldo pendiente. En t=0 retorna el monto original.
        """
        if tem <= 0.0:
            return monto * (1.0 - t / n)
        factor_n = (1.0 + tem) ** n
        factor_t = (1.0 + tem) ** t
        return monto * (factor_n - factor_t) / (factor_n - 1.0)

    @staticmethod
    def vector_saldos(monto: float, tem: float, n: int) -> np.ndarray:
        """Retorna un array con los saldos al inicio de cada mes [1..n].

        Args:
            monto: capital desembolsado.
            tem: tasa efectiva mensual.
            n: plazo total en meses.

        Returns:
            Array de n elementos. El elemento i es el saldo antes de
            pagar el mes i+1.
        """
        t = np.arange(0, n, dtype=float)
        if tem <= 0.0:
            return monto * (1.0 - t / n)
        factor_n = (1.0 + tem) ** n
        factor_t = (1.0 + tem) ** t
        return monto * (factor_n - factor_t) / (factor_n - 1.0)

    def cronograma(self, monto: float, tem: float, n: int) -> pd.DataFrame:
        """Genera el cronograma completo de pagos mes a mes.

        Args:
            monto: capital desembolsado.
            tem: tasa efectiva mensual.
            n: plazo total en meses.

        Returns:
            DataFrame con columnas mes, cuota, interes, amortizacion, saldo.
        """
        c = self.cuota(monto, tem, n)
        saldos_inicio = self.vector_saldos(monto, tem, n)
        intereses = saldos_inicio * tem
        amortizaciones = c - intereses
        saldos_fin = np.maximum(saldos_inicio - amortizaciones, 0.0)
        return pd.DataFrame({
            "mes": np.arange(1, n + 1),
            "cuota": c,
            "interes": intereses,
            "amortizacion": amortizaciones,
            "saldo": saldos_fin,
        })
