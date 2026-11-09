import calendar
import contextlib
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fuso import FusoFixo  # noqa: E402
import wake  # noqa: E402
from lib.autosave import Painel  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402

CMUX = calendar.timegm((2026, 10, 31, 5, 37, 52))


def snap(tipo="apply"):
    abas = [{"uuid": "U%d" % n, "ref": "surface:%d" % n, "sessao": "%d" % n * 8,
             "titulo": "t%d" % n, "cwd": "/tmp", "tipo": "terminal", "transcript": {"path": "/t"}}
            for n in (1, 2, 3, 4)]
    plano = [{"surface": "U1", "acao": "controle"}] + [
        {"surface": "U%d" % n, "acao": "encerrar"} for n in (2, 3, 4)]
    return {"gerado_em": "2026-10-31T05:36:55Z", "tipo": tipo, "plano": plano, "janelas": [
        {"uuid": "W", "ref": "window:1", "workspaces": [{"uuid": "S", "ref": "workspace:1",
                                                          "nome": "proj", "panes": [
                                                              {"uuid": "P", "abas": abas}]}]}]}


def estado(vivos):
    abas = [Aba(uuid="U%d" % n, ref="surface:%d" % n, tipo="terminal", titulo="t%d" % n,
                sessao="%d" % n * 8 if n in vivos else None,
                fonte="processo" if n in vivos else None, pid=str(n) if n in vivos else None)
            for n in (1, 2, 3, 4)]
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="proj",
                  panes=[Pane(uuid="P", ref="pane:1", abas=abas)])])])


class Base(FusoFixo, unittest.TestCase):
    def rodar(self, *argv, dados=None, vivos=(1,), inicios=None, armadas=(), cmux=CMUX,
              autosave_ok=True, tty=False, nome="2026-10-31T05-36-55Z"):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            d = base / nome
            d.mkdir()
            (d / "snapshot.json").write_text(json.dumps(dados or snap()))
            paineis = {"U%d" % n: Painel(surface="U%d" % n, janela="W", workspace="S",
                                         sessao=None, cwd=None, armado="agent")
                       for n in armadas}

            def ler_autosave():
                if not autosave_ok:
                    raise RuntimeError("sem autosave")
                return 0.0, paineis

            self.subir = mock.Mock(return_value=True)
            saida, erro = io.StringIO(), io.StringIO()
            with mock.patch.object(wake, "ler_estado", lambda: estado(set(vivos))), \
                    mock.patch.object(wake, "ler_autosave", ler_autosave), \
                    mock.patch.object(wake, "inicios_de",
                                      lambda pids: dict(inicios or {"1": CMUX + 3})), \
                    mock.patch.object(wake, "inicio_do_cmux", lambda: cmux), \
                    mock.patch.object(wake, "subir", self.subir), \
                    mock.patch.object(sys.stdin, "isatty", lambda: tty), \
                    mock.patch.object(sys, "argv", ["wake.py", "--estado", str(base),
                                                    "--max-age", "1000000", *argv]), \
                    contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
                rc = wake.main()
        self.saida, self.erro = saida.getvalue(), erro.getvalue()
        return rc


class TestWake(Base):
    def test_primeira_linha_mostra_a_hora_de_brasilia(self):
        """E' a linha que o usuario le no terminal: hora de Brasilia, com a zona."""
        dados = {"gerado_em": "2026-10-03T22:30:00Z", "tipo": "apply", "janelas": []}
        self.assertEqual(self.rodar(dados=dados, nome="2026-10-03T22-30-00Z"), 0)
        primeira = self.saida.splitlines()[0]
        self.assertTrue(primeira.startswith("Snapshot de 03/10/2026 19:30 BRT ("), primeira)
        self.assertIn(" · 2026-10-03T22-30-00Z · apply", primeira)

    def test_caso_de_31_10_subiram_sozinhas_nao_e_nada_a_corrigir(self):
        rc = self.rodar(vivos=(1, 2, 3), inicios={"1": CMUX + 3, "2": CMUX + 2, "3": CMUX + 2})
        self.assertEqual(rc, 1)
        self.assertIn("subiu sozinha  2  FALHA", self.saida)
        self.assertIn("22222222", self.saida)
        self.assertNotIn("Nada a corrigir", self.saida)

    def test_tudo_dormindo_e_nada_a_corrigir(self):
        self.rodar()
        self.assertIn("dormindo       3", self.saida)
        self.assertIn("controle       1  (rodando)", self.saida)
        self.assertIn("Nada a corrigir", self.saida)
        self.assertNotIn("sobem ao abrir", self.saida)

    def test_acordada_por_voce_com_a_hora_em_brt(self):
        rc = self.rodar(vivos=(1, 2), inicios={"1": CMUX + 3,
                                               "2": calendar.timegm((2026, 10, 31, 5, 52, 0))})
        self.assertEqual(rc, 0)
        self.assertIn("acordada por voce as 02:52 BRT", self.saida)
        self.assertIn("Nada a corrigir", self.saida)

    def test_armada_sem_processo_e_aviso(self):
        self.rodar(armadas=(3,))
        self.assertIn("armada         1  aviso", self.saida)
        self.assertNotIn("Nada a corrigir", self.saida)

    def test_sem_autosave_nao_diz_nada_a_corrigir(self):
        self.rodar(autosave_ok=False)
        self.assertIn("'armada' nao foi conferida", self.erro)
        self.assertNotIn("Nada a corrigir", self.saida)

    def test_antes_do_cmd_q_avisa_que_a_conferencia_e_depois(self):
        self.rodar(cmux=CMUX - 86400)
        self.assertIn("nao foi reaberto desde este snapshot", self.saida)

    def test_snapshot_velho_sem_terminal_avisa_e_nao_pergunta(self):
        """F4: pelo agente nao ha TTY, e o input() quebrava com EOFError."""
        with mock.patch("builtins.input", side_effect=AssertionError("perguntou")):
            rc = self.rodar("--max-age", "0")
        self.assertEqual(rc, 0)
        self.assertIn("snapshot com mais de 0 dias", self.saida)

    def test_up_retoma_as_que_dormem(self):
        self.rodar("--up", "all", armadas=(4,))
        self.assertEqual(sorted(c.args[0]["sessao"] for c in self.subir.call_args_list),
                         ["22222222", "33333333", "44444444"])
        self.assertIn("Subindo 3 sessoes", self.saida)

    def test_falha_sai_1(self):
        """Item 12."""
        rc = self.rodar(vivos=(1, 2), inicios={"1": CMUX + 3, "2": CMUX + 2})
        self.assertEqual(rc, 1)

    def test_controle_que_nao_subiu_e_falha(self):
        """Item 6."""
        rc = self.rodar(vivos=())
        self.assertEqual(rc, 1)
        self.assertIn("FALHA: a aba de controle nao subiu", self.saida)
        self.assertNotIn("Nada a corrigir", self.saida)

    def test_cedo_demais_pede_para_rodar_de_novo(self):
        """Item 3: o restore leva alguns segundos por aba depois de o cmux abrir."""
        with mock.patch.object(wake.time, "time", return_value=CMUX + 30):
            rc = self.rodar()
        self.assertIn("o restore pode nao ter terminado", self.saida)
        self.assertNotIn("Nada a corrigir", self.saida)
        self.assertEqual(rc, 0)

    def test_suspeita_e_falha(self):
        dados = snap()
        dados["plano"][1]["resultado"] = {"verificado": False, "erro": "x"}
        rc = self.rodar(dados=dados, vivos=(1, 2),
                        inicios={"1": CMUX + 3, "2": calendar.timegm((2026, 10, 31, 5, 52, 0))})
        self.assertEqual(rc, 1)
        self.assertIn("suspeita", self.saida)

    def test_sem_snapshot_de_apply_sai_2(self):
        self.assertEqual(self.rodar(dados=snap(tipo="dry-run")), 2)
        self.assertIn("nenhum snapshot de --apply", self.erro)


if __name__ == "__main__":
    unittest.main()
