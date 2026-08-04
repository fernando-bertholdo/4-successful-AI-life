import pathlib
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Estado, Janela, Workspace  # noqa: E402
from lib.restore import filtrar_alvo, layout_do_workspace, planejar_rebuild  # noqa: E402

ITENS = [
    {"sessao": "1111", "workspace": "projeto-alfa", "titulo": "a", "cwd": "/tmp/a"},
    {"sessao": "2222", "workspace": "projeto-beta", "titulo": "b", "cwd": "/tmp/b"},
]

WS_SNAP = {"uuid": "S", "ref": "workspace:1", "nome": "proj", "panes": [
    {"uuid": "P1", "ref": "pane:1", "abas": [
        {"uuid": "A1", "tipo": "terminal", "sessao": "1111", "cwd": "/tmp/a", "titulo": "t1"},
        {"uuid": "A2", "tipo": "terminal", "sessao": None, "cwd": None, "titulo": "shell"}]},
    {"uuid": "P2", "ref": "pane:2", "abas": [
        {"uuid": "A3", "tipo": "browser", "url": "https://exemplo.com", "titulo": "web"}]}]}


class TestRestore(unittest.TestCase):
    def test_filtra_all(self):
        self.assertEqual(len(filtrar_alvo(ITENS, "all")), 2)

    def test_filtra_por_workspace(self):
        self.assertEqual([x["sessao"] for x in filtrar_alvo(ITENS, "projeto-alfa")], ["1111"])

    def test_layout_um_pane(self):
        ws = {"uuid": "S", "nome": "p", "panes": [WS_SNAP["panes"][0]]}
        layout = layout_do_workspace(ws)
        self.assertIn("pane", layout)
        cmds = [s.get("command") for s in layout["pane"]["surfaces"]]
        self.assertTrue(any(c and "--resume 1111" in c for c in cmds))

    def test_layout_dois_panes_vira_split(self):
        layout = layout_do_workspace(WS_SNAP)
        self.assertEqual(layout["direction"], "horizontal")
        self.assertEqual(len(layout["children"]), 2)

    def test_layout_preserva_browser(self):
        segundo = layout_do_workspace(WS_SNAP)["children"][1]["pane"]["surfaces"][0]
        self.assertEqual(segundo["type"], "browser")
        self.assertEqual(segundo["url"], "https://exemplo.com")

    def test_rebuild_so_planeja_workspace_ausente(self):
        dados = {"janelas": [{"uuid": "W", "ref": "window:1", "workspaces": [
            WS_SNAP, {"uuid": "S2", "ref": "workspace:2", "nome": "existente", "panes": []}]}]}
        estado = Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
            Workspace(uuid="S2", ref="workspace:2", nome="existente", panes=[])])])
        self.assertEqual([p["nome"] for p in planejar_rebuild(dados, estado)], ["proj"])


if __name__ == "__main__":
    unittest.main()
