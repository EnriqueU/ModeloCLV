"""
Orquestador del modelo CLV.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from clv.amortizacion import AmortizacionFrancesa
from clv.buscador_tea import BuscadorTEA
from clv.costos import CostoHandler
from clv.data_loader import DataLoader
from clv.engine import CLVEngine
from clv.pd_curvas import PDCurva
from clv.schemas import OperacionInput, OperacionOutput
from clv.tasas import TasaCurva


class CLVWrapper:
    """Inicializa todos los componentes en el orden correcto.

    Args:
        data_dir: carpeta donde están los archivos CSV de referencia.
    """

    def __init__(self, data_dir: str | Path = ".") -> None:
        self._loader = DataLoader(data_dir)

        # Construye la cadena de dependencias
        costos = CostoHandler(self._loader.costos)
        tasas = TasaCurva(self._loader.transferencia)
        pd_curva = PDCurva(self._loader.pd)
        amort = AmortizacionFrancesa()

        self._engine = CLVEngine(costos, tasas, pd_curva, amort)
        self._buscador = BuscadorTEA(self._engine)

    def procesar(
        self,
        df_input: pd.DataFrame,
    ) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
        """Para el flujo CLI que lee parametros.csv directamente.

        Args:
            df_input: DataFrame con columnas id_operacion, producto,
                      moneda, monto, plazo_meses y roa_target.

        Returns:
            Tupla con:
            - df_resultado: una fila por operación con tea, clv_unitario
              y error_optimizacion.
            - curvas_dict: diccionario {id_operacion: df_curvas} con el
              detalle mes a mes de cada operación.
        """
        resultados: list[dict] = []
        curvas_dict: dict[str, pd.DataFrame] = {}

        for _, fila in df_input.iterrows():
            id_op = str(fila["id_operacion"])
            prod = str(fila["producto"])
            mon = str(fila["moneda"])
            monto = float(fila["monto"])
            n = int(fila["plazo_meses"])
            roa = float(fila["roa_target"])

            tea, error = self._buscador.buscar(roa, prod, mon, monto, n)
            clv, df_curva = self._engine.calcular_con_curvas(tea, prod, mon, monto, n)

            resultados.append({
                "id_operacion": id_op,
                "producto": prod,
                "moneda": mon,
                "monto": monto,
                "plazo_meses": n,
                "roa_target": roa,
                "tea": tea,
                "clv_unitario": clv,
                "error_optimizacion": error,
            })
            curvas_dict[id_op] = df_curva

        return pd.DataFrame(resultados), curvas_dict

    def procesar_operacion(
        self,
        op: OperacionInput,
    ) -> tuple[OperacionOutput, pd.DataFrame]:
        """Procesa una sola operación y retorna el resultado con curvas.
        Usado por la API REST para el endpoint POST /calcular.

        Args:
            op: objeto OperacionInput ya validado por Pydantic.

        Returns:
            Tupla (OperacionOutput, df_curvas).
        """
        tea, error = self._buscador.buscar(
            op.roa_target, op.producto, op.moneda, op.monto, op.plazo_meses
        )
        clv, df_curva = self._engine.calcular_con_curvas(
            tea, op.producto, op.moneda, op.monto, op.plazo_meses
        )
        output = OperacionOutput(
            id_operacion=op.id_operacion,
            producto=op.producto,
            moneda=op.moneda,
            monto=op.monto,
            plazo_meses=op.plazo_meses,
            roa_target=op.roa_target,
            tea=tea,
            clv_unitario=clv,
            error_optimizacion=error,
        )
        return output, df_curva
