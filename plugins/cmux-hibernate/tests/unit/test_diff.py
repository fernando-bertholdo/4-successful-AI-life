import calendar
import json
import pathlib
import sys
import tempfile
import time
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fuso import FusoFixo  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402
from lib.diff import carregar_snapshot, comparar, idade_em_dias  # noqa: E402

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


class TestIdade(FusoFixo, unittest.TestCase):
    FUSO = "America/Sao_Paulo"

    def test_idade_em_dias_formato_antigo(self):
        """Snapshot gravado ate' a 0.1.0: hora local do host, sem zona (14:22:31 em -03 = 17:22:31Z)."""
        base = calendar.timegm((2026, 8, 4, 17, 22, 31))
        self.assertAlmostEqual(idade_em_dias(SNAP, base + 2 * 86400), 2.0, places=6)

    def test_idade_em_dias_formato_utc(self):
        snap = dict(SNAP, gerado_em="2026-10-03T22:30:00Z")
        base = calendar.timegm((2026, 10, 3, 22, 30, 0))
        self.assertAlmostEqual(idade_em_dias(snap, base + 2 * 86400), 2.0, places=6)


class TestCarregarSnapshot(FusoFixo, unittest.TestCase):
    def _grava(self, base, nome, gerado_em):
        d = base / nome
        d.mkdir()
        (d / "snapshot.json").write_text(json.dumps({"gerado_em": gerado_em}))

    def test_le_snapshot_gravado_antes_do_conserto(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            self._grava(base, "2026-08-04T14-22-31", "2026-08-04T14:22:31")
            dados, origem = carregar_snapshot(base)
            self.assertEqual(origem.name, "2026-08-04T14-22-31")
            self.assertGreater(idade_em_dias(dados, time.time()), 0)

    def test_escolhe_o_mais_recente_entre_os_dois_formatos(self):
        """A ordem e' a do instante, nao a do nome: hora local e UTC nao se comparam como texto."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            # Em Toquio (UTC+9), 07:00 local de 04/10 e' 22:00Z de 03/10: uma hora antes do novo.
            self._grava(base, "2026-10-04T07-00-00", "2026-10-04T07:00:00")
            self._grava(base, "2026-10-03T23-00-00Z", "2026-10-03T23:00:00Z")
            _, origem = carregar_snapshot(base)
            self.assertEqual(origem.name, "2026-10-03T23-00-00Z")


if __name__ == "__main__":
    unittest.main()
