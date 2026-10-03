"""Fixa o fuso do processo durante um teste.

Teste de hora local que herda o fuso do host so' discrimina em alguns fusos: a
ordem por nome passava em America/Sao_Paulo e em UTC, e so' falhava a leste de UTC.
"""
import os
import time


class FusoFixo:
    FUSO = "Asia/Tokyo"

    def setUp(self):
        super().setUp()
        anterior = os.environ.get("TZ")
        self.addCleanup(self._restaurar, anterior)
        os.environ["TZ"] = self.FUSO
        time.tzset()

    @staticmethod
    def _restaurar(anterior):
        if anterior is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = anterior
        time.tzset()
