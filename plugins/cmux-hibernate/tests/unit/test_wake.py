import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fuso import FusoFixo  # noqa: E402
import wake  # noqa: E402
from lib.cmux_state import Estado  # noqa: E402


class TestWake(FusoFixo, unittest.TestCase):
    def test_primeira_linha_mostra_a_hora_de_brasilia(self):
        """E' a linha que o usuario le no terminal: hora de Brasilia, com a zona."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            d = base / "2026-10-03T22-30-00Z"
            d.mkdir()
            (d / "snapshot.json").write_text(json.dumps(
                {"gerado_em": "2026-10-03T22:30:00Z", "janelas": []}))
            saida = io.StringIO()
            with mock.patch.object(wake, "BASE_ESTADO", base), \
                    mock.patch.object(wake, "ler_estado", lambda: Estado(janelas=[])), \
                    mock.patch.object(sys, "argv", ["wake.py", "--max-age", "1000000"]), \
                    contextlib.redirect_stdout(saida):
                self.assertEqual(wake.main(), 0)
        primeira = saida.getvalue().splitlines()[0]
        self.assertTrue(primeira.startswith("Snapshot de 03/10/2026 19:30 BRT ("), primeira)
        self.assertTrue(primeira.endswith(" · 2026-10-03T22-30-00Z"), primeira)


if __name__ == "__main__":
    unittest.main()
