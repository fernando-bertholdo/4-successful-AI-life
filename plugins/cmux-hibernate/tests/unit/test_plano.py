"""O plano por aba e a execucao do --apply, com as dependencias do sistema trocadas."""
import pathlib
import sys
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.autosave import Painel  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402
from lib.plano import (  # noqa: E402
    CONTROLE, DORMINDO, ENCERRAR, LIMPAR, PULAR, executar, para_snapshot, planejar)

S = {n: "%d%d%d%d%d%d%d%d-0000-4000-8000-000000000000" % ((n,) * 8) for n in range(1, 8)}


def aba(uuid, n, pid=None, armada=None, mtime=0.0, fonte="processo"):
    return Aba(uuid=uuid, ref="surface:%d" % n, tipo="terminal", titulo="aba %d" % n,
               sessao=S[n], cwd="/tmp/%d" % n, fonte=fonte if pid else "autosave", pid=pid,
               armada=armada, transcript={"path": "/t/%d.jsonl" % n, "kb": 1, "mtime": mtime})


def estado(*abas):
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="ws",
                  panes=[Pane(uuid="P", ref="pane:1", abas=list(abas) + [
                      Aba(uuid="SHELL", ref="surface:9", tipo="terminal", titulo="shell")])])])])


def padrao():
    return estado(aba("CTRL", 1, pid="100", armada="agent"),
                  aba("OCIOSA", 2, pid="200", armada="agent"),
                  aba("OCUPADA", 3, pid="300", armada="agent", mtime=995.0),
                  aba("ARMADA", 4, armada="agent"),
                  aba("DORME", 5),
                  aba("EU", 6, pid="600", armada="agent"))


def acoes(plano):
    return {p["surface"]: p["acao"] for p in plano}


class TestPlanejar(unittest.TestCase):
    def plano(self, e=None, **kw):
        kw.setdefault("controle", "CTRL")
        kw.setdefault("protegidos", {"600"})
        return planejar(e or padrao(), agora=1000.0, hooks={}, **kw)

    def test_cada_aba_ganha_a_acao_certa(self):
        self.assertEqual(acoes(self.plano()), {
            "CTRL": CONTROLE, "OCIOSA": ENCERRAR, "OCUPADA": PULAR, "ARMADA": LIMPAR,
            "DORME": DORMINDO, "EU": PULAR})

    def test_motivos_de_pular(self):
        m = {p["surface"]: p["motivo"] for p in self.plano()}
        self.assertIn("ocupada", m["OCUPADA"])
        self.assertIn("/exit", m["EU"])

    def test_ocupada_pelo_hook(self):
        p = planejar(padrao(), controle="CTRL", agora=1000.0, protegidos=set(),
                     hooks={S[2]: {"runtimeStatus": "running"}})
        self.assertEqual(acoes(p)["OCIOSA"], PULAR)

    def test_all_inclui_o_controle(self):
        self.assertEqual(acoes(self.plano(controle=None))["CTRL"], ENCERRAR)

    def test_aba_sem_sessao_fica_fora(self):
        self.assertNotIn("SHELL", acoes(self.plano()))

    def test_sessao_duplicada_e_pulada(self):
        p = self.plano(duplicadas=[S[2]])
        self.assertEqual(acoes(p)["OCIOSA"], PULAR)
        self.assertIn("mais de uma aba", next(x["motivo"] for x in p if x["surface"] == "OCIOSA"))

    def test_surface_planeja_so_a_aba_pedida_mesmo_a_de_controle(self):
        self.assertEqual(acoes(self.plano(so_aba="OCIOSA")), {"OCIOSA": ENCERRAR})
        self.assertEqual(acoes(self.plano(so_aba="CTRL")), {"CTRL": ENCERRAR})

    def test_surface_duplicada_ou_sem_sessao(self):
        self.assertEqual(acoes(self.plano(so_aba="OCIOSA", duplicadas=[S[2]])), {"OCIOSA": PULAR})
        self.assertEqual(self.plano(so_aba="SHELL"), [])

    def test_plano_carrega_ids_cwd_e_sessao(self):
        item = next(p for p in self.plano() if p["surface"] == "OCIOSA")
        self.assertEqual((item["janela"], item["workspace"], item["sessao"], item["cwd"]),
                         ("W", "S", S[2], "/tmp/2"))

    def test_surface_na_propria_sessao_e_pulada(self):
        self.assertEqual(acoes(self.plano(so_aba="EU")), {"EU": PULAR})

    def test_para_snapshot_tira_o_pid(self):
        for item in para_snapshot(self.plano()):
            self.assertNotIn("pid", item)


class TestExecutar(unittest.TestCase):
    """Os casos do --apply com encerrar, limpar e conferir trocados por dublês."""

    def rodar(self, conferencias, nao_sai=(), confere=True, ocupada=None):
        plano = planejar(padrao(), controle="CTRL", agora=1000.0, hooks={}, protegidos={"600"})
        for p in plano:
            p["inicio"] = 1.0 if p["pid"] else None
        paineis = {p["surface"]: Painel(surface=p["surface"], janela="W", workspace="S",
                                        sessao=p["sessao"], cwd=None, armado="agent")
                   for p in plano}
        self.encerrar = mock.Mock(return_value=set(nao_sai))
        self.limpar = mock.Mock(return_value="OK")
        self.conferir = mock.Mock(side_effect=list(conferencias))
        executar(plano, paineis, confere=lambda pid, s, inicio: confere,
                 encerrar_fn=self.encerrar, limpar_fn=self.limpar, conferir_fn=self.conferir,
                 ocupada_fn=lambda item: ocupada, agora=lambda: 1000.0)
        return {p["surface"]: p for p in plano}

    def test_caminho_feliz(self):
        r = self.rodar([{"OCIOSA": None, "ARMADA": None}])
        self.assertEqual(r["OCIOSA"]["resultado"]["metodo"], "sigterm")
        self.assertTrue(r["OCIOSA"]["resultado"]["verificado"])
        self.assertEqual(r["ARMADA"]["resultado"]["metodo"], "rpc")
        self.assertTrue(r["ARMADA"]["resultado"]["verificado"])
        self.assertIsNone(r["DORME"]["resultado"])  # quem confere e' a conferencia_final
        self.assertFalse(r["OCUPADA"]["resultado"]["verificado"])
        self.assertIsNone(r["CTRL"]["resultado"])
        self.encerrar.assert_called_once_with(["200"])
        self.assertEqual([c.args[0].surface for c in self.limpar.call_args_list], ["ARMADA"])
        self.assertRegex(r["OCIOSA"]["resultado"]["quando"], r"Z$")

    def test_sigterm_que_nao_desarma_cai_na_reserva(self):
        r = self.rodar([{"OCIOSA": "continua armada (agent)", "ARMADA": None}, {"OCIOSA": None}])
        self.assertEqual(r["OCIOSA"]["resultado"]["metodo"], "sigterm+rpc")
        self.assertTrue(r["OCIOSA"]["resultado"]["verificado"])

    def test_ok_que_nao_pegou_reprova(self):
        """O caso de 31/10: a ferramenta responde OK e o autosave continua armado."""
        r = self.rodar([{"OCIOSA": "continua armada (agent)", "ARMADA": "continua armada (agent)"},
                        {"OCIOSA": "continua armada (agent)"}])
        for s in ("OCIOSA", "ARMADA"):
            self.assertFalse(r[s]["resultado"]["verificado"], s)
            self.assertIn("continua armada", r[s]["resultado"]["erro"])

    def test_processo_que_nao_sai_nao_e_conferido_nem_limpo(self):
        r = self.rodar([{"ARMADA": None}], nao_sai={"200"})
        self.assertFalse(r["OCIOSA"]["resultado"]["verificado"])
        self.assertIn("SIGKILL", r["OCIOSA"]["resultado"]["erro"])
        self.assertEqual(self.conferir.call_args_list[0].args[0], ["ARMADA"])

    def test_processo_que_mudou_nao_recebe_sinal(self):
        r = self.rodar([{"ARMADA": None}], confere=False)
        self.encerrar.assert_called_once_with([])
        self.assertIn("mudou", r["OCIOSA"]["resultado"]["erro"])

    def test_rpc_que_explode_nao_derruba_o_apply(self):
        """Sem cmux no PATH ou com timeout, o rpc levanta; a conferencia decide o resultado."""
        plano = planejar(padrao(), controle="CTRL", agora=1000.0, hooks={}, protegidos={"600"})
        for p in plano:
            p["inicio"] = 1.0 if p["pid"] else None
        limpar = mock.Mock(side_effect=RuntimeError("cmux nao encontrado"))
        executar(plano, {}, confere=lambda pid, s, inicio: True, encerrar_fn=lambda pids: set(),
                 limpar_fn=limpar, conferir_fn=lambda ss, depois_de, iniciais: {
                     s: "continua armada (agent)" for s in ss},
                 agora=lambda: 1000.0)
        r = {p["surface"]: p["resultado"] for p in plano}
        self.assertFalse(r["ARMADA"]["verificado"])
        self.assertIn("cmux nao encontrado", r["ARMADA"]["erro"])

    def test_pid_sem_instante_de_nascimento_nao_recebe_sinal(self):
        """Sem o lstart da leitura inicial nao ha como barrar pid reusado."""
        plano = planejar(padrao(), controle="CTRL", agora=1000.0, hooks={}, protegidos={"600"})
        encerrar = mock.Mock(return_value=set())
        executar(plano, {}, confere=lambda *a: True, encerrar_fn=encerrar,
                 limpar_fn=mock.Mock(), conferir_fn=lambda ss, depois_de, iniciais: {},
                 agora=lambda: 1000.0)
        encerrar.assert_called_once_with([])
        item = next(p for p in plano if p["surface"] == "OCIOSA")
        self.assertIn("nasceu", item["resultado"]["erro"])

    def test_sessao_que_entrou_em_turno_e_pulada_na_hora(self):
        r = self.rodar([{"ARMADA": None}], ocupada="transcript escrito ha 2 s")
        self.assertEqual(r["OCIOSA"]["acao"], PULAR)
        self.assertFalse(r["OCIOSA"]["resultado"]["verificado"])
        self.encerrar.assert_called_once_with([])


if __name__ == "__main__":
    unittest.main()
