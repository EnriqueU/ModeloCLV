"""
Entry point del modelo CLV — modo línea de comandos.

Uso:
    PYTHONPATH=src python main.py
"""
from __future__ import annotations

import time
from pathlib import Path

import pandas as pd

from clv.wrapper import CLVWrapper

DATA_DIR = Path(__file__).parent / "data"


def main() -> None:
    print("=" * 60)
    print("  Modelo CLV — cálculo de TEA óptima por ROA target")
    print("=" * 60)

    t0 = time.perf_counter()
    wrapper = CLVWrapper(DATA_DIR)
    df_input = pd.read_csv(DATA_DIR / "parametros.csv")

    print(f"\nProcesando {len(df_input)} operaciones...\n")
    df_out, curvas = wrapper.procesar(df_input)
    elapsed = time.perf_counter() - t0

    print("─" * 80)
    cols = ["id_operacion", "producto", "moneda", "tea", "clv_unitario", "error_optimizacion"]
    print(df_out[cols].to_string(index=False))
    print("─" * 80)
    print(f"\nTiempo total: {elapsed:.3f}s para {len(df_input)} operaciones")

    # Mostrar curvas de la primera operación como ejemplo
    primer_id = df_out["id_operacion"].iloc[0]
    print(f"\nDetalle de flujos para {primer_id} (primeros 4 meses):")
    print(curvas[primer_id].head(4).to_string(index=False))


if __name__ == "__main__":
    main()
