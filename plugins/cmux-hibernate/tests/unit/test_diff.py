import pathlib
import sys
import time
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402
from lib.diff import comparar, idade_em_dias  # noqa: E402

SNAP = {
    "gerado_em": "2026-08-04T14:22:31",
    "janelas": [{"uuid": "W", "ref": "window:1", "workspaces": [{
        "uuid": "S", "ref": "workspace:1", "nome": "proj", "panes": [{
            "uuid": "P", "ref": "pane:1", "abas": [
                {"uuid": "A1", "sessao": "1111", "titulo": "viva", "cwd": "/tmp/a",
                 "tipo": "terminal", "transcript": {"path": "/t1.jsonl"}},
                {"uuid": "A2", "sessao": "2222", "titulo": "dormindo", "cwd": "/tmp/b",
                 "tipo": "terminal", "transcript": {"path": "/t2.jsonl"}},
                {"uuid": "A3", "sessao": "3333", "titulo": "sumiu", "cwd": "/tmp/c",
                 "tipo": "terminal", "transcript": {"path": "/t3.jsonl"}},
            ]}]}]}]}


def estado_atual():
    viva = Aba(uuid="A1", ref="surface:1", tipo="terminal", titulo="viva",
               sessao="1111", fonte="processo")
    dormindo = Aba(uuid="A2", ref="surface:2", tipo="terminal", titulo="dormindo")
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="proj",
                  panes=[Pane(uuid="P", ref="pane:1", abas=[viva, dormindo])])])])


class TestDiff(unittest.TestCase):
    def setUp(self):
        self.r = comparar(SNAP, estado_atual())

    def test_identifica_viva(self):
        self.assertEqual([x["sessao"] for x in self.r["vivas"]], ["1111"])

    def test_identifica_dormindo(self):
        """Aba existe na estrutura mas nenhum processo roda a sessao."""
        self.assertEqual([x["sessao"] for x in self.r["dormindo"]], ["2222"])

    def test_identifica_ausente(self):
        """Aba do snapshot que nao existe mais na estrutura atual."""
        self.assertEqual([x["sessao"] for x in self.r["ausentes"]], ["3333"])

    def test_chave_e_sessao_nao_titulo(self):
        """Titulos mentem: uma aba pode exibir o nome de outro projeto."""
        snap = {"janelas": [{"uuid": "W", "ref": "w", "workspaces": [{
            "uuid": "S", "ref": "s", "nome": "n", "panes": [{"uuid": "P", "ref": "p", "abas": [
                {"uuid": "A1", "sessao": "1111", "titulo": "TITULO COMPLETAMENTE DIFERENTE",
                 "cwd": "/tmp/a", "tipo": "terminal",
                 "transcript": {"path": "/t.jsonl"}}]}]}]}]}
        self.assertEqual(len(comparar(snap, estado_atual())["vivas"]), 1)

    def test_idade_em_dias(self):
        base = time.mktime(time.strptime("2026-08-04T14:22:31", "%Y-%m-%dT%H:%M:%S"))
        self.assertAlmostEqual(idade_em_dias(SNAP, base + 2 * 86400), 2.0, places=1)


if __name__ == "__main__":
    unittest.main()
