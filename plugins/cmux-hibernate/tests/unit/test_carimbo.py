import calendar
import pathlib
import sys
import time
import unittest
from datetime import datetime, timezone

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fuso import FusoFixo  # noqa: E402
from lib.carimbo import (agora_utc, instante_do_nome, ler, mostrar,  # noqa: E402
                         nome_de_diretorio)


class TestLer(unittest.TestCase):
    def test_formato_novo_e_utc(self):
        dt = ler("2026-10-03T22:30:00Z")
        self.assertEqual(dt.timestamp(), calendar.timegm((2026, 10, 3, 22, 30, 0)))

    def test_offset_explicito(self):
        self.assertEqual(ler("2026-10-03T19:30:00-03:00"), ler("2026-10-03T22:30:00Z"))

    def test_formato_invalido_falha(self):
        with self.assertRaises(ValueError):
            ler("ontem")


class TestGravar(unittest.TestCase):
    def test_agora_utc_termina_em_z(self):
        self.assertRegex(agora_utc(), r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_agora_utc_e_o_instante_atual(self):
        self.assertLess(abs(ler(agora_utc()).timestamp() - time.time()), 2)

    def test_nome_de_diretorio_em_utc_com_z(self):
        dt = datetime(2026, 10, 4, 1, 30, 5, tzinfo=timezone.utc)
        self.assertEqual(nome_de_diretorio(dt), "2026-10-04T01-30-05Z")


class TestInstanteDoNome(unittest.TestCase):
    def test_nome_novo(self):
        self.assertEqual(instante_do_nome("2026-10-04T01-30-05Z"),
                         datetime(2026, 10, 4, 1, 30, 5, tzinfo=timezone.utc))

    def test_nome_alheio(self):
        self.assertIsNone(instante_do_nome("notas"))


class TestMostrar(unittest.TestCase):
    def test_hora_de_brasilia_com_zona(self):
        self.assertEqual(mostrar("2026-10-03T22:30:00Z"), "03/10/2026 19:30 BRT")

    def test_data_e_a_do_calendario_de_brasilia(self):
        """Das 21:00 as 23:59 em Brasilia, o UTC ja' esta' no dia seguinte."""
        self.assertEqual(mostrar("2026-10-04T01:30:00Z"), "03/10/2026 22:30 BRT")


class TestFormatoAntigo(FusoFixo, unittest.TestCase):
    """Snapshots ate' a 0.1.0 gravaram hora local sem zona. Num host a -03,
    14:22:31 local e' 17:22:31Z; sob UTC a leitura errada coincidiria com a certa."""
    FUSO = "America/Sao_Paulo"

    def test_gerado_em_antigo_e_hora_local_do_host(self):
        self.assertEqual(ler("2026-08-04T14:22:31").timestamp(),
                         calendar.timegm((2026, 8, 4, 17, 22, 31)))

    def test_nome_antigo_e_hora_local_do_host(self):
        self.assertEqual(instante_do_nome("2026-08-04T14-22-31").timestamp(),
                         calendar.timegm((2026, 8, 4, 17, 22, 31)))

    def test_formato_antigo_tambem_e_mostrado(self):
        self.assertEqual(mostrar("2026-08-04T14:22:31"), "04/08/2026 14:22 BRT")


if __name__ == "__main__":
    unittest.main()
