"""
Lectura de archivos de datos del modelo CLV.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd


class DataLoader:
    """Lee los CSVs estáticos del modelo y los deja listos en memoria.

    Args:
        data_dir: carpeta donde viven los archivos CSV. Por defecto
                  busca en el directorio actual.
    """

    def __init__(self, data_dir: str | Path = ".") -> None:
        self._data_dir = Path(data_dir)
        self.costos: pd.DataFrame = self._leer("costos.csv")
        self.transferencia: pd.DataFrame = self._leer("transferencia.csv")
        self.pd: pd.DataFrame = self._leer("pd.csv")

    def _leer(self, nombre: str) -> pd.DataFrame:
        """Lee un CSV y lo retorna como DataFrame.

        Args:
            nombre: nombre del archivo dentro de data_dir.

        Returns:
            DataFrame con el contenido del archivo.
        """
        ruta = self._data_dir / nombre
        if not ruta.exists():
            raise FileNotFoundError(
                f"No encontré el archivo '{nombre}' en '{self._data_dir}'. "
                f"Ruta esperada: {ruta.resolve()}"
            )
        return pd.read_csv(ruta)

    def parametros(self) -> pd.DataFrame:
        """Carga y retorna el archivo de operaciones a procesar.

        Returns:
            DataFrame con las operaciones (id, producto, moneda, monto,
            plazo_meses, roa_target).
        """
        return self._leer("parametros.csv")
