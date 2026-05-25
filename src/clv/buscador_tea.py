"""
Optimizador de TEA dado un ROA target.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

from clv.engine import CLVEngine

# Rango de búsqueda para la TEA
_TEA_MIN: float = 0.001   # 0.1% — por debajo de esto no tiene sentido financiero
_TEA_MAX: float = 0.990   # 99%  — por encima tampoco
_TOL_ABS: float = 1e-8    # precisión del optimizador
_MAX_ITER: int = 100       # tope de iteraciones (brentq suele usar ~15)


class BuscadorTEA:
    """Encuentra la TEA óptima tal que CLV(TEA) == roa_target.

    Args:
        engine: instancia de CLVEngine para evaluar el CLV.
    """

    def __init__(self, engine: CLVEngine) -> None:
        self._engine = engine

    def buscar(
        self,
        roa_target: float,
        producto: str,
        moneda: str,
        monto: float,
        n: int,
    ) -> tuple[float, float]:
        """Busca la TEA que hace CLV(TEA) = roa_target.

        Args:
            roa_target: retorno objetivo sobre activos (ej: 0.05 = 5%).
            producto: tipo de producto financiero.
            moneda: PEN o USD.
            monto: capital desembolsado.
            n: plazo en meses.

        Returns:
            Tupla (tea_optima, error_absoluto) donde error_absoluto
            es |CLV(tea_optima) - roa_target|. Debería ser < 1e-7.
        """

        def objetivo(tea: float) -> float:
            return self._engine.calcular(tea, producto, moneda, monto, n) - roa_target

        f_min = objetivo(_TEA_MIN)
        f_max = objetivo(_TEA_MAX)

        # Caso normal: la raíz está dentro del rango estándar
        if f_min * f_max < 0:
            tea_opt = brentq(
                objetivo, _TEA_MIN, _TEA_MAX,
                xtol=_TOL_ABS, maxiter=_MAX_ITER
            )
            return tea_opt, abs(objetivo(tea_opt))
        return self._buscar_con_barrido(objetivo, roa_target, producto, moneda, monto, n)

    def _buscar_con_barrido(
        self,
        objetivo,
        roa_target: float,
        producto: str,
        moneda: str,
        monto: float,
        n: int,
    ) -> tuple[float, float]:
        """Fallback: barrido de 32 puntos para localizar la raíz.

        Args:
            objetivo: función a minimizar (CLV - roa_target).
            los demás args son para recalcular el error final.

        Returns:
            Tupla (tea_optima, error_absoluto).
        """
        candidatas = np.linspace(_TEA_MIN, _TEA_MAX, 32)
        errores = np.array([abs(objetivo(t)) for t in candidatas])
        mejor = float(candidatas[int(np.argmin(errores))])

        lo = max(_TEA_MIN, mejor - 0.05)
        hi = min(_TEA_MAX, mejor + 0.05)

        if objetivo(lo) * objetivo(hi) < 0:
            tea_opt = brentq(objetivo, lo, hi, xtol=_TOL_ABS, maxiter=_MAX_ITER)
            return tea_opt, abs(objetivo(tea_opt))

        error = abs(self._engine.calcular(mejor, producto, moneda, monto, n) - roa_target)
        return mejor, error
