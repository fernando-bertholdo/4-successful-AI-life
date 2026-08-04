import pathlib
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Estado, parse_tree  # noqa: E402

FIXTURE = (RAIZ / "tests/fixtures/tree.txt").read_text()


class TestParseTree(unittest.TestCase):
    def setUp(self):
        self.janelas = parse_tree(FIXTURE)
        self.estado = Estado(janelas=self.janelas)

    def test_encontra_janelas(self):
        self.assertGreater(len(self.janelas), 0)
        for j in self.janelas:
            self.assertRegex(j.uuid, r"^[0-9A-F-]{36}$")
            self.assertRegex(j.ref, r"^window:\d+$")

    def test_workspaces_tem_nome(self):
        nomes = [w.nome for j in self.janelas for w in j.workspaces]
        self.assertGreater(len(nomes), 0)
        self.assertTrue(all(isinstance(n, str) for n in nomes))

    def test_abas_carregam_tipo_e_uuid(self):
        abas = [a for *_, a in self.estado.todas_abas()]
        self.assertGreater(len(abas), 0)
        for a in abas:
            self.assertIn(a.tipo, {"terminal", "browser", "markdown"})
            self.assertRegex(a.uuid, r"^[0-9A-F-]{36}$")

    def test_hierarquia_preservada(self):
        for janela, ws, pane, _aba in self.estado.todas_abas():
            self.assertIn(pane, ws.panes)
            self.assertIn(ws, janela.workspaces)

    def test_browser_captura_url(self):
        browsers = [a for *_, a in self.estado.todas_abas() if a.tipo == "browser"]
        for b in browsers:
            self.assertTrue(b.url is None or b.url.startswith("http"))


if __name__ == "__main__":
    unittest.main()
