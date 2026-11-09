import json
import pathlib
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fuso import FusoFixo  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402
from lib.snapshot import (  # noqa: E402
    NOME_DRY_RUN, aplicar_retencao, gravar, gravar_dry_run, serializar)


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

    def test_tipo_e_plano_vao_no_snapshot(self):
        plano = [{"surface": "U1", "acao": "encerrar", "resultado": {"verificado": True}}]
        d = serializar(estado_exemplo(), None, 7, tipo="apply", plano=plano, escopo="padrao",
                       versao_cmux="cmux 0.65.2")
        self.assertEqual((d["tipo"], d["escopo"], d["versao_cmux"]), ("apply", "padrao",
                                                                       "cmux 0.65.2"))
        self.assertEqual(d["plano"], plano)
        self.assertRegex(d["versao_plugin"] or "", r"^\d+\.\d+\.\d+$")

    def test_tipo_padrao_e_dry_run(self):
        self.assertEqual(serializar(estado_exemplo(), None, 7)["tipo"], "dry-run")

    def test_gerado_em_e_utc_com_z(self):
        d = serializar(estado_exemplo(), aba_controle=None, stale_days=7)
        self.assertRegex(d["gerado_em"], r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")

    def test_diretorio_e_o_instante_de_gerado_em_em_utc(self):
        dados = dict(serializar(estado_exemplo(), "U1", 7), gerado_em="2026-10-04T01:30:05Z")
        with tempfile.TemporaryDirectory() as tmp:
            destino = gravar(dados, pathlib.Path(tmp))
            self.assertEqual(destino.name, "2026-10-04T01-30-05Z")


class TestComandoDoInventario(unittest.TestCase):
    def test_cwd_com_aspas_e_espaco_vai_citado(self):
        """Uma pasta com apostrofo quebrava o comando colado no terminal."""
        e = estado_exemplo()
        e.janelas[0].workspaces[0].panes[0].abas[0].cwd = "/tmp/o'neil dir"
        with tempfile.TemporaryDirectory() as tmp:
            destino = gravar(serializar(e, None, 7), pathlib.Path(tmp))
            texto = (destino / "INVENTARIO.md").read_text()
        self.assertIn("cd '/tmp/o'\"'\"'neil dir' && claude --resume", texto)


class TestDryRun(unittest.TestCase):
    """O dry-run nao entra na retencao dos 5 nem e' o que o wake compara (F6, F5)."""

    def test_dry_run_vai_para_diretorio_fixo_e_sobrescreve(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            for i in range(7):
                (base / ("2026-08-04T10-00-0%dZ" % i)).mkdir()
            d1 = gravar_dry_run(serializar(estado_exemplo(), None, 7), base)
            (d1 / "lixo").write_text("x")
            d2 = gravar_dry_run(serializar(estado_exemplo(), None, 7), base)
            self.assertEqual((d1, d2.name), (d2, NOME_DRY_RUN))
            self.assertFalse((d2 / "lixo").exists())
            self.assertTrue((d2 / "INVENTARIO.md").exists())
            self.assertEqual(len([d for d in base.iterdir() if d.name.endswith("Z")]), 7)

    def test_retencao_nao_conta_nem_apaga_o_dry_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            gravar_dry_run(serializar(estado_exemplo(), None, 7), base)
            for i in range(6):
                (base / ("2026-08-04T10-00-0%dZ" % i)).mkdir()
            removidos = aplicar_retencao(base, manter=5)
            self.assertEqual([d.name for d in removidos], ["2026-08-04T10-00-00Z"])
            self.assertTrue((base / NOME_DRY_RUN).exists())


class TestInventario(FusoFixo, unittest.TestCase):
    """Fora de Brasilia: em America/Sao_Paulo a hora do host coincidiria com a certa."""

    def test_inventario_mostra_hora_de_brasilia_com_zona(self):
        dados = dict(serializar(estado_exemplo(), "U1", 7), gerado_em="2026-10-04T01:30:05Z")
        with tempfile.TemporaryDirectory() as tmp:
            texto = (gravar(dados, pathlib.Path(tmp)) / "INVENTARIO.md").read_text()
            self.assertIn("**Gerado:** 03/10/2026 22:30 BRT (2026-10-04T01:30:05Z)", texto)


class TestRetencao(FusoFixo, unittest.TestCase):
    def test_retencao_ordena_pelo_instante_entre_os_dois_formatos(self):
        """Nome antigo (hora local) e nome novo (UTC) nao se comparam como texto."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            # Em Toquio (UTC+9), 07:00 local de 04/10 e' 22:00Z de 03/10: uma hora antes do novo.
            for nome in ("2026-10-04T07-00-00", "2026-10-03T23-00-00Z"):
                (base / nome).mkdir()
            removidos = aplicar_retencao(base, manter=1)
            self.assertEqual([d.name for d in removidos], ["2026-10-04T07-00-00"])

    def test_retencao_nao_toca_diretorio_alheio(self):
        """So' sai o que o carimbo reconhece como snapshot; o resto e' de quem o pos ali."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            for nome in ["2026-08-04T10-00-0%d" % i for i in range(6)] + ["guardar-antes-do-conserto"]:
                (base / nome).mkdir()
                (base / nome / "snapshot.json").write_text("{}")
            removidos = aplicar_retencao(base, manter=5)
            self.assertEqual([d.name for d in removidos], ["2026-08-04T10-00-00"])
            self.assertTrue((base / "guardar-antes-do-conserto").exists())

    def test_retencao_mantem_os_cinco_mais_recentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            for i in range(8):
                d = base / ("2026-08-04T10-00-0%d" % i)
                d.mkdir()
                (d / "snapshot.json").write_text("{}")
            removidos = aplicar_retencao(base, manter=5)
            self.assertEqual(len(removidos), 3)
            self.assertEqual(len(list(base.iterdir())), 5)


if __name__ == "__main__":
    unittest.main()
