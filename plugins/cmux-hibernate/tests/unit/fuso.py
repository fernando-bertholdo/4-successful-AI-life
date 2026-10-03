"""Fixa o fuso do processo durante um teste.

Teste de hora local que herda o fuso do host so' discrimina em alguns fusos: num
host a frente de UTC, a ordem por nome pode escolher o antigo, quando o intervalo
entre os dois snapshots e' menor que o adiantamento do fuso; em America/Sao_Paulo
e em UTC ela nunca erra, e o teste passava com o defeito.
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
