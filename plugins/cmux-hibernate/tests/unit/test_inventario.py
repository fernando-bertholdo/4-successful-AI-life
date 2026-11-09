"""Aba sem processo entra no inventario: armada pelo autosave, dormindo pelo snapshot anterior."""
import pathlib
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.autosave import Painel  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace, aplicar_processos  # noqa: E402
from lib.inventario import completar_inventario  # noqa: E402

VIVA, ARMADA, DORMIA, SHELL = "AAAA0001", "AAAA0002", "AAAA0003", "AAAA0004"


def estado():
    abas = [Aba(uuid=VIVA, ref="surface:1", tipo="terminal", titulo="viva",
                sessao="s-viva", cwd="/tmp/v", fonte="processo", pid="101"),
            Aba(uuid=ARMADA, ref="surface:2", tipo="terminal", titulo="armada"),
            Aba(uuid=DORMIA, ref="surface:3", tipo="terminal", titulo="dormia"),
            Aba(uuid=SHELL, ref="surface:4", tipo="terminal", titulo="shell")]
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="ws",
                  panes=[Pane(uuid="P", ref="pane:1", abas=abas)])])])


def p(surface, sessao, armado, cwd="/tmp/x"):
    return Painel(surface=surface, janela="W", workspace="S", sessao=sessao, cwd=cwd,
                  armado=armado)


ANTERIOR = {"tipo": "apply", "janelas": [{"uuid": "W", "workspaces": [{"uuid": "S", "panes": [
    {"uuid": "P", "abas": [
        {"uuid": DORMIA, "sessao": "s-dormia", "cwd": "/tmp/d", "titulo": "dormia"},
        {"uuid": "SUMIU", "sessao": "s-sumiu", "cwd": "/tmp/z", "titulo": "sumiu"}]}]}]}]}


class TestCompletar(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.raiz = pathlib.Path(self.tmp.name)
        (self.raiz / "proj").mkdir()
        (self.raiz / "proj" / "s-armada.jsonl").write_text('{"cwd": "/tmp/a"}\n')
        self.e = estado()
        paineis = {VIVA: p(VIVA, "s-viva", "agent"), ARMADA: p(ARMADA, "s-armada", "agent")}
        self.n = completar_inventario(self.e, paineis, ANTERIOR, raiz=self.raiz)
        self.abas = {a.uuid: a for *_, a in self.e.todas_abas()}

    def test_armada_sem_processo_vem_do_autosave(self):
        a = self.abas[ARMADA]
        self.assertEqual((a.sessao, a.fonte, a.armada, a.pid), ("s-armada", "autosave", "agent",
                                                                 None))
        self.assertEqual(a.transcript["path"], str(self.raiz / "proj" / "s-armada.jsonl"))

    def test_quem_ja_dormia_vem_do_snapshot_anterior(self):
        a = self.abas[DORMIA]
        self.assertEqual((a.sessao, a.fonte, a.cwd, a.armada), ("s-dormia", "snapshot", "/tmp/d",
                                                                None))
        self.assertIsNone(a.transcript)

    def test_processo_nao_e_sobrescrito_mas_ganha_o_estado_armado(self):
        a = self.abas[VIVA]
        self.assertEqual((a.sessao, a.fonte, a.armada), ("s-viva", "processo", "agent"))

    def test_shell_sem_registro_fica_sem_sessao(self):
        self.assertIsNone(self.abas[SHELL].sessao)

    def test_aba_do_snapshot_que_nao_existe_mais_nao_entra(self):
        self.assertNotIn("SUMIU", self.abas)
        self.assertEqual(self.n, {"autosave": 1, "snapshot": 1})

    def test_autosave_vence_o_snapshot_anterior(self):
        e = estado()
        completar_inventario(e, {DORMIA: p(DORMIA, "s-nova", None)}, ANTERIOR, raiz=self.raiz)
        a = next(x for *_, x in e.todas_abas() if x.uuid == DORMIA)
        self.assertEqual((a.sessao, a.fonte), ("s-nova", "autosave"))

    def test_aba_com_processo_sem_id_no_argv_leva_o_pid(self):
        """Processo vivo cujo binding nao foi lido: nao pode virar 'limpar' com o claude de pe."""
        e = estado()
        e.processos = {ARMADA: "777"}
        completar_inventario(e, {ARMADA: p(ARMADA, "s-armada", "agent")}, None, raiz=self.raiz)
        a = next(x for *_, x in e.todas_abas() if x.uuid == ARMADA)
        self.assertEqual((a.sessao, a.pid), ("s-armada", "777"))

    def test_sem_anterior(self):
        e = estado()
        self.assertEqual(completar_inventario(e, {}, None, raiz=self.raiz),
                         {"autosave": 0, "snapshot": 0})


class TestPid(unittest.TestCase):
    def test_aplicar_processos_guarda_o_pid(self):
        e = estado()
        aplicar_processos(e, {ARMADA: {"sessao": "s-x", "pid": "202"}}, cwds={})
        a = next(x for *_, x in e.todas_abas() if x.uuid == ARMADA)
        self.assertEqual(a.pid, "202")


if __name__ == "__main__":
    unittest.main()
