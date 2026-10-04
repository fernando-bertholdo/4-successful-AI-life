"""O main() do hibernate.py com --surface, sem cmux: estado, ps e escrita sao trocados."""
import contextlib
import io
import pathlib
import sys
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
import hibernate  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402

S1 = "11111111-1111-1111-1111-111111111111"
S2 = "22222222-2222-2222-2222-222222222222"


def estado():
    abas = [Aba(uuid="CTRL", ref="surface:1", tipo="terminal", titulo="controle",
                sessao=S1, cwd="/tmp/a", fonte="processo"),
            Aba(uuid="OUTRA", ref="surface:2", tipo="terminal", titulo="outra",
                sessao=S2, cwd="/tmp/b", fonte="processo"),
            Aba(uuid="SHELL", ref="surface:3", tipo="terminal", titulo="shell")]
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="ws",
                  panes=[Pane(uuid="P", ref="pane:1", abas=abas)])])])


class TestMainSurface(unittest.TestCase):
    def rodar(self, *argv, duplicadas=(), desarme_ok=True, controle="CTRL"):
        gravar = mock.Mock(return_value=pathlib.Path("/tmp/snap"))
        desarmar = mock.Mock(return_value=desarme_ok)
        serializar = mock.Mock(return_value={})
        saida, erro = io.StringIO(), io.StringIO()
        with mock.patch.object(hibernate, "ler_estado", return_value=estado()), \
                mock.patch.object(hibernate, "_ps_eww", return_value=""), \
                mock.patch.object(hibernate, "detectar_duplicatas", return_value=list(duplicadas)), \
                mock.patch.object(hibernate, "serializar", serializar), \
                mock.patch.object(hibernate, "gravar", gravar), \
                mock.patch.object(hibernate, "aplicar_retencao"), \
                mock.patch.object(hibernate, "desarmar", desarmar), \
                mock.patch.dict("os.environ", {"CMUX_SURFACE_ID": controle}), \
                mock.patch.object(sys, "argv", ["hibernate.py", *argv]), \
                contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
            try:
                rc = hibernate.main()
            except SystemExit as e:
                rc = e.code
        return rc, saida.getvalue(), erro.getvalue(), gravar, desarmar, serializar

    def test_surface_vazio_sai_2_sem_snapshot_nem_desarme(self):
        rc, _, erro, gravar, desarmar, _ = self.rodar("--surface", "", "--apply")
        self.assertEqual(rc, 2)
        self.assertIn("nenhuma", erro)
        gravar.assert_not_called()
        desarmar.assert_not_called()

    def test_surface_inexistente_sai_2_sem_snapshot(self):
        rc, _, _, gravar, _, _ = self.rodar("--surface", "surface:99")
        self.assertEqual(rc, 2)
        gravar.assert_not_called()

    def test_surface_sem_sessao_sai_2(self):
        rc, _, erro, gravar, _, _ = self.rodar("--surface", "surface:3")
        self.assertEqual((rc, "nao tem sessao" in erro), (2, True))
        gravar.assert_not_called()

    def test_all_com_surface_e_recusado(self):
        rc, _, _, _, _, _ = self.rodar("--all", "--surface", "surface:2")
        self.assertEqual(rc, 2)

    def test_dry_run_lista_so_a_aba_pedida(self):
        rc, saida, _, _, desarmar, _ = self.rodar("--surface", "surface:2")
        self.assertEqual(rc, 0)
        self.assertIn("Aba pedida: 22222222", saida)
        self.assertIn("Desarmaria 1 abas", saida)
        desarmar.assert_not_called()

    def test_apply_desarma_a_propria_aba_de_controle(self):
        rc, saida, _, _, desarmar, serializar = self.rodar("--surface", "ctrl", "--apply")
        self.assertEqual(rc, 0)
        self.assertEqual(desarmar.call_args.args[2], "CTRL")
        self.assertEqual(desarmar.call_count, 1)
        self.assertIsNone(serializar.call_args.args[1])  # o snapshot nao a chama de controle
        self.assertIn("Pode dar Cmd+Q", saida)

    def test_apply_em_aba_duplicada_sai_1_sem_cmd_q(self):
        rc, saida, erro, _, desarmar, _ = self.rodar("--surface", "surface:2", "--apply",
                                                     duplicadas=[S2])
        self.assertEqual(rc, 1)
        self.assertNotIn("Cmd+Q", saida)
        self.assertIn("continua armada", erro)
        desarmar.assert_not_called()

    def test_apply_com_desarme_falho_sai_1(self):
        rc, saida, _, _, _, _ = self.rodar("--surface", "surface:2", "--apply", desarme_ok=False)
        self.assertEqual(rc, 1)
        self.assertNotIn("Cmd+Q", saida)

    def test_sem_surface_segue_preservando_o_controle(self):
        rc, _, _, _, desarmar, serializar = self.rodar("--apply")
        self.assertEqual(rc, 0)
        self.assertEqual([c.args[2] for c in desarmar.call_args_list], ["OUTRA"])
        self.assertEqual(serializar.call_args.args[1], "CTRL")


if __name__ == "__main__":
    unittest.main()
