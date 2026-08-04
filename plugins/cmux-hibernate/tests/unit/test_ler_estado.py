import pathlib
import sys
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib import cmux_state  # noqa: E402

FIX_TREE = (RAIZ / "tests/fixtures/tree.txt").read_text()
FIX_PS = (RAIZ / "tests/fixtures/ps-eww.txt").read_text()


class TestLerEstado(unittest.TestCase):
    def test_orquestra_sem_tocar_no_sistema(self):
        with mock.patch.object(cmux_state, "rodar_cmux", return_value=FIX_TREE), \
             mock.patch.object(cmux_state, "_ps_eww", return_value=FIX_PS), \
             mock.patch.object(cmux_state, "resolver_cwd", return_value="/tmp/x"), \
             mock.patch.object(cmux_state, "localizar_transcript", return_value=None):
            estado = cmux_state.ler_estado()
        abas = [a for *_, a in estado.todas_abas()]
        self.assertGreater(len(abas), 0)
        com_sessao = [a for a in abas if a.sessao]
        self.assertGreater(len(com_sessao), 0)
        self.assertTrue(all(a.fonte == "processo" for a in com_sessao))

    def test_cmux_bin_respeita_env(self):
        with mock.patch.dict("os.environ", {"CMUX_BUNDLED_CLI_PATH": "/custom/cmux"}), \
             mock.patch("os.path.exists", return_value=True):
            self.assertEqual(cmux_state.cmux_bin(), "/custom/cmux")


if __name__ == "__main__":
    unittest.main()
