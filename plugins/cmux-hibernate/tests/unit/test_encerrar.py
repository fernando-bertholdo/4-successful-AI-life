"""Encerrar, limpar e conferir: nenhum sucesso sem o autosave regravado dizer que sim."""
import json
import pathlib
import signal
import sys
import unittest
from unittest import mock

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib import encerrar  # noqa: E402
from lib.autosave import Painel  # noqa: E402

SURF = "B0000001-0000-4000-8000-000000000001"


class Relogio:
    """Tempo falso: dormir avanca o relogio, e cada chamada ve o instante atual."""

    def __init__(self, t=1000.0):
        self.t = t

    def __call__(self):
        return self.t

    def dormir(self, s):
        self.t += s


class TestOcupada(unittest.TestCase):
    def test_transcript_recente_e_ocupada(self):
        m = encerrar.motivo_ocupada("s", 990.0, {}, agora=1000.0)
        self.assertIn("transcript escrito ha 10 s", m)

    def test_transcript_antigo_e_hook_ocioso_e_ociosa(self):
        hooks = {"s": {"runtimeStatus": "idle", "agentLifecycle": "idle"}}
        self.assertIsNone(encerrar.motivo_ocupada("s", 100.0, hooks, agora=1000.0))

    def test_hook_em_turno_ou_esperando_e_ocupada(self):
        for reg in ({"runtimeStatus": "running"}, {"runtimeStatus": "needsInput"},
                    {"runtimeStatus": "error", "updatedAt": 999.0},
                    {"runtimeStatus": "idle", "agentLifecycle": "backgroundWorkPending"},
                    {"runtimeStatus": "idle", "agentLifecycle": "running"}):
            self.assertIsNotNone(encerrar.motivo_ocupada("s", 100.0, {"s": reg}, agora=1000.0),
                                 reg)

    def test_transcript_mais_recente_do_projeto_conta(self):
        """Depois de um /clear a sessao escreve noutro .jsonl do mesmo projeto."""
        m = encerrar.motivo_ocupada("s", [100.0, 995.0], {}, agora=1000.0)
        self.assertIn("ha 5 s", m)

    def test_hook_achado_pela_aba(self):
        hooks = {"outra": {"surfaceId": "b0000001-0000-4000-8000-000000000001",
                           "runtimeStatus": "running"}}
        self.assertIsNotNone(encerrar.motivo_ocupada("s", 100.0, hooks, agora=1000.0,
                                                     surface=SURF))
        self.assertIsNone(encerrar.motivo_ocupada("s", 100.0, hooks, agora=1000.0))

    def test_error_antigo_nao_prende_a_aba_para_sempre(self):
        velho = {"s": {"runtimeStatus": "error", "updatedAt": 100.0}}
        novo = {"s": {"runtimeStatus": "error", "updatedAt": 990.0}}
        self.assertIsNone(encerrar.motivo_ocupada("s", 100.0, velho, agora=1000.0))
        self.assertIsNotNone(encerrar.motivo_ocupada("s", 100.0, novo, agora=1000.0))

    def test_sem_transcript_e_sem_hook_e_ociosa(self):
        self.assertIsNone(encerrar.motivo_ocupada("s", None, {}, agora=1000.0))


class TestAncestrais(unittest.TestCase):
    def test_sobe_a_cadeia_ate_o_launchd(self):
        pais = {"50": "40", "40": "30", "30": "1", "1": "0"}
        self.assertEqual(encerrar.ancestrais("50", ppid=pais.get), {"50", "40", "30", "1"})

    def test_para_em_ciclo_ou_falha_de_leitura(self):
        self.assertEqual(encerrar.ancestrais("50", ppid={"50": "50"}.get), {"50"})
        self.assertEqual(encerrar.ancestrais("50", ppid=lambda p: None), {"50"})


ARGS = "/Users/x/.local/bin/claude --resume abc --dangerously-skip-permissions"
ENV = ARGS + " CMUX_SURFACE_ID=%s HOME=/x" % SURF


class TestProcessoConfere(unittest.TestCase):
    def confere(self, args=ARGS, env=ENV, inicio=500.0, agora=500.0, surface=SURF):
        return encerrar.processo_confere("9", surface, inicio=inicio, args_de=lambda p: args,
                                         env_de=lambda p: env, inicio_de=lambda p: agora)

    def test_mesmo_claude_da_mesma_aba(self):
        self.assertTrue(self.confere())
        self.assertTrue(self.confere(surface=SURF.lower()))

    def test_outra_aba_ou_outro_binario(self):
        outra = "B0000002-0000-4000-8000-000000000002"
        self.assertFalse(self.confere(env=ENV.replace(SURF, outra)))
        self.assertFalse(self.confere(args="/bin/zsh -l"))
        self.assertFalse(self.confere(args="", env=""))

    def test_nao_aceita_variavel_de_outro_nome_nem_o_daemon(self):
        self.assertFalse(self.confere(env=ENV.replace(" CMUX_SURFACE_ID",
                                                      " OUTRA_CMUX_SURFACE_ID")))
        self.assertFalse(self.confere(args="/Users/x/.local/bin/claude daemon run"))

    def test_o_binario_vem_do_argv_e_nao_do_ambiente(self):
        """Com `eww`, um claude no PATH do ambiente de um zsh passaria por claude."""
        env = "/bin/zsh PATH=/Users/x/.local/bin/claude CMUX_SURFACE_ID=%s" % SURF
        self.assertFalse(self.confere(args="/bin/zsh", env=env))

    def test_pid_reusado_e_recusado(self):
        self.assertFalse(self.confere(inicio=500.0, agora=777.0))
        self.assertFalse(self.confere(inicio=500.0, agora=None))


class TestEncerrar(unittest.TestCase):
    def test_sigterm_e_espera_sair(self):
        r = Relogio()
        vivos = {"10", "20"}
        enviados = []

        def matar(pid, sinal):
            enviados.append((pid, sinal))
            vivos.discard(str(pid))

        restantes = encerrar.encerrar(["10", "20"], matar=matar, vivo=lambda p: p in vivos,
                                      dormir=r.dormir, relogio=r)
        self.assertEqual(restantes, set())
        self.assertEqual(enviados, [(10, signal.SIGTERM), (20, signal.SIGTERM)])

    def test_quem_nao_sai_no_teto_e_reportado_sem_sigkill(self):
        r = Relogio()
        enviados = []
        restantes = encerrar.encerrar(["10"], matar=lambda p, s: enviados.append(s),
                                      vivo=lambda p: True, dormir=r.dormir, relogio=r, teto=10)
        self.assertEqual(restantes, {"10"})
        self.assertEqual(enviados, [signal.SIGTERM])
        self.assertGreaterEqual(r.t, 1010.0)

    def test_processo_que_ja_saiu_nao_e_erro(self):
        def matar(p, s):
            raise ProcessLookupError

        self.assertEqual(encerrar.encerrar(["10"], matar=matar, vivo=lambda p: False,
                                           dormir=lambda s: None, relogio=Relogio()), set())


class TestLimpar(unittest.TestCase):
    def test_rpc_com_o_contrato_do_hook(self):
        rpc = mock.Mock(return_value='{"cleared": true}')
        p = Painel(surface=SURF, janela="W", workspace="WS", sessao="sess", cwd=None,
                   armado="agent")
        encerrar.limpar_registro(p, rodar=rpc)
        metodo, payload = rpc.call_args.args[1], json.loads(rpc.call_args.args[2])
        self.assertEqual((rpc.call_args.args[0], metodo), ("rpc", "surface.resume.clear"))
        self.assertEqual(payload, {"window_id": "W", "workspace_id": "WS", "surface_id": SURF,
                                   "checkpoint_id": "sess", "source": "agent-hook",
                                   "agent_session_ended": True})


def painel(armado):
    return Painel(surface=SURF, janela="W", workspace="WS", sessao="s", cwd=None, armado=armado)


class TestConferir(unittest.TestCase):
    def test_exige_save_posterior_a_acao(self):
        """Um autosave anterior a acao nao prova nada, mesmo dizendo 'desarmada'."""
        r = Relogio(1000.0)
        ler = mock.Mock(return_value=(999.0, {SURF: painel(None)}))
        res = encerrar.conferir([SURF], depois_de=1000.0, ler=ler, dormir=r.dormir, relogio=r,
                                teto=5)
        self.assertEqual(res, {SURF: "o cmux nao regravou o autosave em 5 s"})

    def test_desarmada_no_save_novo(self):
        r = Relogio(1000.0)
        leituras = iter([(999.0, {SURF: painel("agent")}), (1002.0, {SURF: painel(None)})])
        res = encerrar.conferir([SURF], depois_de=1000.0, ler=lambda: next(leituras),
                                dormir=r.dormir, relogio=r)
        self.assertEqual(res, {SURF: None})

    def test_painel_que_sumiu_do_autosave_nao_e_conferido(self):
        r = Relogio(1000.0)
        outro = "B0000009-0000-4000-8000-000000000009"
        res = encerrar.conferir([SURF], depois_de=1000.0, iniciais={SURF},
                                ler=lambda: (1001.0, {outro: painel(None)}), dormir=r.dormir,
                                relogio=r, teto=2)
        self.assertEqual(res, {SURF: "o painel sumiu do autosave"})

    def test_autosave_sem_paineis_de_terminal_nao_confere_nada(self):
        r = Relogio(1000.0)
        res = encerrar.conferir([SURF], depois_de=1000.0, ler=lambda: (1001.0, {}),
                                dormir=r.dormir, relogio=r, teto=2)
        self.assertEqual(res, {SURF: "o autosave nao tem paineis de terminal"})

    def test_continua_armada_ate_o_teto(self):
        r = Relogio(1000.0)
        res = encerrar.conferir([SURF], depois_de=1000.0,
                                ler=lambda: (r.t, {SURF: painel("binding agent-hook")}),
                                dormir=r.dormir, relogio=r, teto=5)
        self.assertEqual(res, {SURF: "continua armada (binding agent-hook)"})

    def test_erro_de_leitura_e_reportado(self):
        r = Relogio(1000.0)

        def ler():
            raise RuntimeError("sem arquivo")

        res = encerrar.conferir([SURF], depois_de=1000.0, ler=ler, dormir=r.dormir, relogio=r,
                                teto=2)
        self.assertEqual(res, {SURF: "sem arquivo"})

    def test_sem_alvos_nao_le_nada(self):
        ler = mock.Mock()
        self.assertEqual(encerrar.conferir([], depois_de=0.0, ler=ler), {})
        ler.assert_not_called()


if __name__ == "__main__":
    unittest.main()
