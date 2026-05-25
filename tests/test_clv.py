"""
Tests del modelo CLV.

Para correr:
    PYTHONPATH=src python -m unittest tests/test_clv.py -v
"""
from __future__ import annotations

import json
import time
import unittest
from pathlib import Path

import pandas as pd

from clv.wrapper import CLVWrapper

DATA_DIR = Path(__file__).parent.parent / "data"


# ---------------------------------------------------------------------------
# Fixtures compartidas
# ---------------------------------------------------------------------------

def _build_wrapper() -> CLVWrapper:
    return CLVWrapper(DATA_DIR)


# ---------------------------------------------------------------------------
# 1. Tests de estructura y consistencia
# ---------------------------------------------------------------------------

class TestEstructuraResultados(unittest.TestCase):
    """Verifica que el output tenga la forma esperada."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = _build_wrapper()
        cls.df_params = pd.read_csv(DATA_DIR / "parametros.csv")
        cls.df_costos = pd.read_csv(DATA_DIR / "costos.csv")
        cls.df_trans = pd.read_csv(DATA_DIR / "transferencia.csv")
        cls.df_pd = pd.read_csv(DATA_DIR / "pd.csv")
        cls.df_res, cls.curvas = cls.wrapper.procesar(cls.df_params)

    def test_resultado_tiene_columna_id(self) -> None:
        self.assertIn("id_operacion", self.df_res.columns)

    def test_resultado_tiene_columna_tea(self) -> None:
        self.assertIn("tea", self.df_res.columns)

    def test_resultado_tiene_10_filas(self) -> None:
        self.assertEqual(len(self.df_res), 10)

    def test_tea_no_tiene_nulos(self) -> None:
        self.assertFalse(self.df_res["tea"].isna().any())

    def test_ids_son_unicos(self) -> None:
        ids = self.df_res["id_operacion"].tolist()
        self.assertEqual(len(ids), len(set(ids)))

    def test_csv_parametros_tiene_10_filas(self) -> None:
        self.assertEqual(len(self.df_params), 10)

    def test_csv_costos_tiene_6_filas(self) -> None:
        self.assertEqual(len(self.df_costos), 6)


# ---------------------------------------------------------------------------
# 2. Tests de rangos y coherencia financiera
# ---------------------------------------------------------------------------

class TestCoherenciaFinanciera(unittest.TestCase):
    """Verifica que los resultados tengan sentido financiero."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = _build_wrapper()
        df = pd.read_csv(DATA_DIR / "parametros.csv")
        cls.df_trans = pd.read_csv(DATA_DIR / "transferencia.csv")
        cls.df_res, _ = cls.wrapper.procesar(df)

    def test_tea_dentro_de_rango_razonable(self) -> None:
        for _, row in self.df_res.iterrows():
            with self.subTest(op=row["id_operacion"]):
                self.assertGreaterEqual(row["tea"], 0.01)
                self.assertLessEqual(row["tea"], 0.99)

    def test_tea_mayor_que_tasa_de_fondeo(self) -> None:
        """La tasa cobrada siempre debe superar el costo de fondeo."""
        for _, row in self.df_res.iterrows():
            tasa_min = self.df_trans[
                (self.df_trans["producto"] == row["producto"]) &
                (self.df_trans["moneda"] == row["moneda"])
            ]["tasa_anual"].min()
            with self.subTest(op=row["id_operacion"]):
                self.assertGreaterEqual(row["tea"], tasa_min)


# ---------------------------------------------------------------------------
# 3. Tests de curvas
# ---------------------------------------------------------------------------

class TestCurvas(unittest.TestCase):
    """Verifica la integridad de las curvas de flujo mes a mes."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = _build_wrapper()
        df = pd.read_csv(DATA_DIR / "parametros.csv")
        cls.df_res, cls.curvas = cls.wrapper.procesar(df)

    def test_curvas_existen_para_cada_operacion(self) -> None:
        for _, row in self.df_res.iterrows():
            self.assertIn(row["id_operacion"], self.curvas)

    def test_curvas_tienen_columnas_requeridas(self) -> None:
        columnas = [
            "mes", "saldo", "cuota", "pd_marginal", "supervivencia",
            "costo_fondeo", "costo_mantenimiento", "flujo_neto",
            "factor_descuento", "vp_flujo",
        ]
        for id_op, df_curva in self.curvas.items():
            for col in columnas:
                with self.subTest(op=id_op, col=col):
                    self.assertIn(col, df_curva.columns)

    def test_curvas_tienen_n_mas_uno_filas(self) -> None:
        """Deben tener n filas de meses + 1 fila del mes 0."""
        for _, row in self.df_res.iterrows():
            id_op = row["id_operacion"]
            esperado = int(row["plazo_meses"]) + 1
            with self.subTest(op=id_op):
                self.assertEqual(len(self.curvas[id_op]), esperado)

    def test_saldo_mes_cero_igual_a_monto(self) -> None:
        for _, row in self.df_res.iterrows():
            id_op = row["id_operacion"]
            saldo_0 = self.curvas[id_op].loc[
                self.curvas[id_op]["mes"] == 0, "saldo"
            ].values[0]
            with self.subTest(op=id_op):
                self.assertAlmostEqual(saldo_0, row["monto"], delta=0.01)

    def test_supervivencia_acotada_entre_0_y_1(self) -> None:
        for id_op, df_curva in self.curvas.items():
            for val in df_curva["supervivencia"]:
                with self.subTest(op=id_op):
                    self.assertGreaterEqual(val, 0.0)
                    self.assertLessEqual(val, 1.0)


# ---------------------------------------------------------------------------
# 4. Tests de calidad numérica
# ---------------------------------------------------------------------------

class TestCalidadNumerica(unittest.TestCase):
    """Verifica que los resultados cumplan la tolerancia requerida."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.wrapper = _build_wrapper()
        df = pd.read_csv(DATA_DIR / "parametros.csv")
        cls.df_res, _ = cls.wrapper.procesar(df)

    def test_error_optimizacion_menor_a_tolerancia(self) -> None:
        for _, row in self.df_res.iterrows():
            with self.subTest(op=row["id_operacion"]):
                self.assertLessEqual(row["error_optimizacion"], 0.01)

    def test_clv_aproxima_roa_target(self) -> None:
        for _, row in self.df_res.iterrows():
            diferencia = abs(row["clv_unitario"] - row["roa_target"])
            with self.subTest(op=row["id_operacion"]):
                self.assertLessEqual(diferencia, 0.01)


# ---------------------------------------------------------------------------
# 5. Tests de rendimiento
# ---------------------------------------------------------------------------

class TestRendimiento(unittest.TestCase):
    """Verifica que el procesamiento cumpla el límite de tiempo."""

    def test_10_operaciones_en_menos_de_60_segundos(self) -> None:
        wrapper = _build_wrapper()
        df = pd.read_csv(DATA_DIR / "parametros.csv")
        t0 = time.perf_counter()
        wrapper.procesar(df)
        elapsed = time.perf_counter() - t0
        self.assertLess(elapsed, 60.0, f"Tiempo excedido: {elapsed:.2f}s")


# ---------------------------------------------------------------------------
# 6. Tests de la API REST
# ---------------------------------------------------------------------------

class TestAPIREST(unittest.TestCase):
    """Tests de los endpoints de la API usando TestClient de FastAPI."""

    @classmethod
    def setUpClass(cls) -> None:
        try:
            from fastapi.testclient import TestClient
            from clv.api import app
            cls.client = TestClient(app)
            cls.disponible = True
        except ImportError:
            cls.disponible = False

    def _skip_si_no_disponible(self) -> None:
        if not self.disponible:
            self.skipTest("FastAPI/httpx no está instalado en este entorno")

    def test_health_retorna_ok(self) -> None:
        self._skip_si_no_disponible()
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["status"], "ok")

    def test_health_retorna_productos(self) -> None:
        self._skip_si_no_disponible()
        resp = self.client.get("/health")
        data = resp.json()
        self.assertIn("productos_disponibles", data)
        self.assertGreater(len(data["productos_disponibles"]), 0)

    def test_calcular_retorna_tea(self) -> None:
        self._skip_si_no_disponible()
        payload = {
            "id_operacion": "TEST001",
            "producto": "Credito",
            "moneda": "PEN",
            "monto": 10000,
            "plazo_meses": 12,
            "roa_target": 0.05,
        }
        resp = self.client.post("/calcular", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("tea", data)
        self.assertGreater(data["tea"], 0)

    def test_calcular_retorna_curvas(self) -> None:
        self._skip_si_no_disponible()
        payload = {
            "producto": "Leasing",
            "moneda": "USD",
            "monto": 30000,
            "plazo_meses": 24,
            "roa_target": 0.055,
        }
        resp = self.client.post("/calcular", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("curvas", data)
        self.assertEqual(len(data["curvas"]), 25)  # mes 0 + 24 meses

    def test_calcular_producto_invalido_retorna_422(self) -> None:
        self._skip_si_no_disponible()
        payload = {
            "producto": "ProductoInexistente",
            "moneda": "PEN",
            "monto": 10000,
            "plazo_meses": 12,
            "roa_target": 0.05,
        }
        resp = self.client.post("/calcular", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_calcular_monto_negativo_retorna_422(self) -> None:
        self._skip_si_no_disponible()
        payload = {
            "producto": "Credito",
            "moneda": "PEN",
            "monto": -5000,
            "plazo_meses": 12,
            "roa_target": 0.05,
        }
        resp = self.client.post("/calcular", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_calcular_lote_retorna_todos(self) -> None:
        self._skip_si_no_disponible()
        payload = {
            "operaciones": [
                {"producto": "Credito", "moneda": "PEN", "monto": 10000,
                 "plazo_meses": 12, "roa_target": 0.05},
                {"producto": "Tarjeta", "moneda": "PEN", "monto": 3000,
                 "plazo_meses": 6, "roa_target": 0.08},
            ]
        }
        resp = self.client.post("/calcular/lote", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_procesadas"], 2)
        self.assertEqual(len(data["resultados"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
