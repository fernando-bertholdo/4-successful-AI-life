import pathlib
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.bindings import abas_que_casam, comando_resume  # noqa: E402
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


class TestUmaAba(unittest.TestCase):
    """--surface: a aba pedida pelo uuid ou pela ref. O plano dela esta em test_plano.py."""

    def uuids(self, alvo, e=None):
        return [a.uuid for a in abas_que_casam(e or estado(), alvo)]

    def test_localiza_por_uuid_em_qualquer_caixa(self):
        self.assertEqual(self.uuids("outra"), ["OUTRA"])

    def test_localiza_por_ref_em_qualquer_caixa_e_com_espacos(self):
        self.assertEqual(self.uuids(" SURFACE:2 "), ["OUTRA"])

    def test_aba_inexistente_nao_casa(self):
        self.assertEqual(self.uuids("surface:99"), [])

    def test_alvo_vazio_nao_casa(self):
        """$CMUX_SURFACE_ID vazio nao pode virar 'todas as abas'."""
        self.assertEqual(self.uuids(""), [])
        self.assertEqual(self.uuids("   "), [])

    def test_ref_repetida_devolve_as_duas(self):
        e = estado()
        e.janelas[0].workspaces[0].panes[0].abas[2].ref = "surface:2"
        self.assertEqual(sorted(self.uuids("surface:2", e)), ["OUTRA", "SHELL"])


if __name__ == "__main__":
    unittest.main()
