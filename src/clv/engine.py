"""
Motor de cálculo del CLV (Customer Lifetime Value).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from clv.amortizacion import AmortizacionFrancesa
from clv.costos import CostoHandler
from clv.pd_curvas import PDCurva
from clv.tasas import TasaCurva


class CLVEngine:
    """Calcula el CLV unitario de una operación dado un TEA.

    Args:
        costos: handler de costos de originación y mantenimiento.
        tasas: curvas de tasa de fondeo por plazo.
        pd_curva: curvas de supervivencia por producto.
        amort: calculador de amortización francesa.
    """

    def __init__(
        self,
        costos: CostoHandler,
        tasas: TasaCurva,
        pd_curva: PDCurva,
        amort: AmortizacionFrancesa,
    ) -> None:
        self._costos = costos
        self._tasas = tasas
        self._pd = pd_curva
        self._amort = amort

    def calcular(
        self,
        tea: float,
        producto: str,
        moneda: str,
        monto: float,
        n: int,
    ) -> float:
        """Retorna el CLV unitario para la TEA dada.

        Args:
            tea: tasa efectiva anual candidata (ej: 0.25 = 25%).
            producto: tipo de producto (Credito, Leasing, Tarjeta).
            moneda: moneda de la operación (PEN, USD).
            monto: capital desembolsado.
            n: plazo en meses.

        Returns:
            CLV unitario como fracción del monto. Si es igual al
            roa_target, la TEA es la correcta.
        """
        clv, _ = self._core(tea, producto, moneda, monto, n, con_curvas=False)
        return clv

    def calcular_con_curvas(
        self,
        tea: float,
        producto: str,
        moneda: str,
        monto: float,
        n: int,
    ) -> tuple[float, pd.DataFrame]:
        """Retorna el CLV y el detalle mes a mes de todos los flujos.

        Args:
            tea: tasa efectiva anual (la óptima encontrada por BuscadorTEA).
            producto: tipo de producto.
            moneda: moneda.
            monto: capital desembolsado.
            n: plazo en meses.

        Returns:
            Tupla (clv_unitario, df_curvas) donde df_curvas tiene una
            fila por mes (incluyendo el mes 0 del desembolso) con todas
            las columnas del flujo.
        """
        return self._core(tea, producto, moneda, monto, n, con_curvas=True)

    def _core(
        self,
        tea: float,
        producto: str,
        moneda: str,
        monto: float,
        n: int,
        con_curvas: bool,
    ) -> tuple[float, pd.DataFrame | None]:
        """Implementación interna vectorizada del cálculo CLV.

        Args:
            tea: tasa efectiva anual.
            producto: tipo de producto.
            moneda: moneda.
            monto: capital desembolsado.
            n: plazo en meses.
            con_curvas: si True, construye y retorna el DataFrame de curvas.

        Returns:
            (clv_unitario, df_curvas | None)
        """
        # Convertir TEA a TEM para el cálculo mensual
        tem = (1.0 + tea) ** (1.0 / 12.0) - 1.0
        cuota = self._amort.cuota(monto, tem, n)

        # Costos fijos para esta combinación producto/moneda
        c_orig = self._costos.costo_originacion(producto, moneda)
        c_mant = self._costos.costo_mantenimiento(producto, moneda)

        # Índices de meses: [1, 2, ..., n]
        meses = np.arange(1, n + 1)

        # Arrays vectorizados — todo calculado de golpe
        saldos = self._amort.vector_saldos(monto, tem, n)

        dias = meses * 30.0
        tasas_fondeo = np.array([
            self._tasas.tasa_en_plazo(producto, moneda, d) for d in dias
        ])

        supervivencia = np.array([
            self._pd.supervivencia(producto, int(t)) for t in meses
        ])

        pd_marginal = np.array([
            self._pd.pd_mes(producto, int(t)) for t in meses
        ])

        # Flujo neto mensual esperado (ponderado por probabilidad de cobro)
        costo_fondeo = saldos * tasas_fondeo / 12.0
        costo_mant = saldos * c_mant / 12.0
        flujo_neto = (cuota - costo_fondeo - costo_mant) * supervivencia

        # Valor presente de cada flujo
        factor_desc = 1.0 / (1.0 + tasas_fondeo / 12.0) ** meses
        vp = flujo_neto * factor_desc

        # CLV: valor generado sobre el monto arriesgado
        clv = (-monto - c_orig * monto + vp.sum()) / monto

        if not con_curvas:
            return clv, None

        # Fila del desembolso (mes 0)
        fila_0 = {
            "mes": 0,
            "saldo": monto,
            "cuota": 0.0,
            "pd_marginal": 0.0,
            "supervivencia": 1.0,
            "costo_fondeo": 0.0,
            "costo_mantenimiento": 0.0,
            "flujo_neto": -monto - c_orig * monto,
            "factor_descuento": 1.0,
            "vp_flujo": -monto - c_orig * monto,
        }

        df_meses = pd.DataFrame({
            "mes": meses,
            "saldo": saldos,
            "cuota": cuota,
            "pd_marginal": pd_marginal,
            "supervivencia": supervivencia,
            "costo_fondeo": costo_fondeo,
            "costo_mantenimiento": costo_mant,
            "flujo_neto": flujo_neto,
            "factor_descuento": factor_desc,
            "vp_flujo": vp,
        })

        df_curvas = pd.concat(
            [pd.DataFrame([fila_0]), df_meses], ignore_index=True
        )
        return clv, df_curvas
