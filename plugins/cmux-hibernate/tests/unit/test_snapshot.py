import json
import pathlib
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402
from lib.snapshot import aplicar_retencao, gravar, serializar  # noqa: E402


def estado_exemplo():
    aba = Aba(uuid="U1", ref="surface:1", tipo="terminal", titulo="tarefa",
              sessao="11111111-2222-3333-4444-555555555555", cwd="/tmp/p",
              fonte="processo", transcript={"path": "/t.jsonl", "kb": 10, "mtime": 1.0})
    return Estado(janelas=[Janela(uuid="W1", ref="window:1", workspaces=[
        Workspace(uuid="S1", ref="workspace:1", nome="proj",
                  panes=[Pane(uuid="P1", ref="pane:1", abas=[aba])])])])


class TestSnapshot(unittest.TestCase):
    def test_serializa_hierarquia_e_metadados(self):
        d = serializar(estado_exemplo(), aba_controle="U1", stale_days=7)
        self.assertEqual(d["aba_de_controle"], "U1")
        self.assertEqual(d["stale_days"], 7)
        aba = d["janelas"][0]["workspaces"][0]["panes"][0]["abas"][0]
        self.assertEqual(aba["sessao"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(aba["fonte"], "processo")

    def test_nao_grava_campo_volatil(self):
        """Nada que afirme estado do momento — envelheceria em silencio."""
        d = serializar(estado_exemplo(), aba_controle=None, stale_days=7)
        aba = d["janelas"][0]["workspaces"][0]["panes"][0]["abas"][0]
        for proibido in ("rodando", "viva", "alive", "pid"):
            self.assertNotIn(proibido, aba)

    def test_grava_snapshot_e_inventario(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = gravar(serializar(estado_exemplo(), "U1", 7), pathlib.Path(tmp))
            self.assertTrue((destino / "snapshot.json").exists())
            self.assertTrue((destino / "INVENTARIO.md").exists())
            lido = json.loads((destino / "snapshot.json").read_text())
            self.assertEqual(lido["aba_de_controle"], "U1")

    def test_retencao_mantem_os_cinco_mais_recentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            for i in range(8):
                d = base / ("2026-08-04T10-0%d" % i)
                d.mkdir()
                (d / "snapshot.json").write_text("{}")
            removidos = aplicar_retencao(base, manter=5)
            self.assertEqual(len(removidos), 3)
            self.assertEqual(len(list(base.iterdir())), 5)


if __name__ == "__main__":
    unittest.main()
