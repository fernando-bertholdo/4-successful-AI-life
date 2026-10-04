import pathlib
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.bindings import comando_resume, localizar_aba, planejar_desarme  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402


def estado():
    a1 = Aba(uuid="CTRL", ref="surface:1", tipo="terminal", titulo="controle",
             sessao="11111111-1111-1111-1111-111111111111", cwd="/tmp/a", fonte="processo")
    a2 = Aba(uuid="OUTRA", ref="surface:2", tipo="terminal", titulo="outra",
             sessao="22222222-2222-2222-2222-222222222222", cwd="/tmp/b", fonte="processo")
    a3 = Aba(uuid="SHELL", ref="surface:3", tipo="terminal", titulo="shell")
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="ws",
                  panes=[Pane(uuid="P", ref="pane:1", abas=[a1, a2, a3])])])])


class TestBindings(unittest.TestCase):
    def test_comando_resume(self):
        self.assertEqual(comando_resume("abc"),
                         ["claude", "--resume", "abc", "--dangerously-skip-permissions"])

    def test_preserva_aba_de_controle(self):
        alvos = [p["surface"] for p in planejar_desarme(estado(), aba_controle="CTRL")]
        self.assertIn("OUTRA", alvos)
        self.assertNotIn("CTRL", alvos)

    def test_ignora_aba_sem_sessao(self):
        alvos = [p["surface"] for p in planejar_desarme(estado(), aba_controle=None)]
        self.assertNotIn("SHELL", alvos)

    def test_sem_controle_desarma_todas(self):
        self.assertEqual(len(planejar_desarme(estado(), aba_controle=None)), 2)

    def test_plano_carrega_cwd_e_sessao(self):
        plano = planejar_desarme(estado(), aba_controle="CTRL")
        self.assertEqual(plano[0]["cwd"], "/tmp/b")
        self.assertEqual(plano[0]["sessao"], "22222222-2222-2222-2222-222222222222")

    def test_pula_sessoes_duplicadas(self):
        """Caso de borda do spec: sessao em duas abas nao e' desarmada."""
        plano = planejar_desarme(estado(), aba_controle=None,
                                 duplicadas=["22222222-2222-2222-2222-222222222222"])
        self.assertEqual([p["sessao"] for p in plano],
                         ["11111111-1111-1111-1111-111111111111"])


class TestUmaAba(unittest.TestCase):
    """--surface: o plano tem so' a aba pedida, mesmo que seja a de controle."""

    def test_localiza_por_uuid_em_qualquer_caixa(self):
        self.assertEqual(localizar_aba(estado(), "outra").uuid, "OUTRA")

    def test_localiza_por_ref(self):
        self.assertEqual(localizar_aba(estado(), "surface:2").uuid, "OUTRA")

    def test_aba_inexistente_e_none(self):
        self.assertIsNone(localizar_aba(estado(), "surface:99"))

    def test_plano_so_com_a_aba_pedida(self):
        plano = planejar_desarme(estado(), aba_controle=None, so_aba="OUTRA")
        self.assertEqual([p["surface"] for p in plano], ["OUTRA"])

    def test_aba_pedida_vence_a_de_controle(self):
        """A sessao velha do revezamento hiberna a propria aba pelo CMUX_SURFACE_ID."""
        plano = planejar_desarme(estado(), aba_controle="CTRL", so_aba="CTRL")
        self.assertEqual([p["surface"] for p in plano], ["CTRL"])

    def test_aba_pedida_duplicada_fica_de_fora(self):
        plano = planejar_desarme(estado(), aba_controle=None, so_aba="OUTRA",
                                 duplicadas=["22222222-2222-2222-2222-222222222222"])
        self.assertEqual(plano, [])

    def test_aba_pedida_sem_sessao_fica_de_fora(self):
        self.assertEqual(planejar_desarme(estado(), aba_controle=None, so_aba="SHELL"), [])


if __name__ == "__main__":
    unittest.main()
