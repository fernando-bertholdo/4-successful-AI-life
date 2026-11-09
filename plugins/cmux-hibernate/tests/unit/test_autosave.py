"""O autosave do cmux e' a fonte que a restauracao le: e' dele que sai "armada"."""
import json
import os
import pathlib
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.autosave import ler_autosave, ler_hooks, motivo_armado  # noqa: E402

FIX_AUTOSAVE = RAIZ / "tests/fixtures/autosave.json"
FIX_HOOKS = RAIZ / "tests/fixtures/claude-hook-sessions.json"
U = lambda n: "B000000%d-0000-4000-8000-00000000000%d" % (n, n)  # noqa: E731
S = lambda n: "%d%d%d%d%d%d%d%d-0000-4000-8000-00000000000%d" % ((n,) * 8 + (n,))  # noqa: E731


class TestMotivoArmado(unittest.TestCase):
    def test_agent_basta(self):
        self.assertEqual(motivo_armado({"agent": {"sessionId": "x"}}), "agent")

    def test_agent_conta_mesmo_com_was_running_false_e_binding_desligado(self):
        """O save do fechamento recalcula o wasAgentRunning: nao e' ele que desarma."""
        t = {"agent": {"sessionId": "x"}, "wasAgentRunning": False,
             "resumeBinding": {"source": "agent-hook", "autoResume": False}}
        self.assertEqual(motivo_armado(t), "agent")

    def test_binding_agent_hook_ligado(self):
        t = {"resumeBinding": {"source": "agent-hook", "autoResume": True}}
        self.assertEqual(motivo_armado(t), "binding agent-hook")

    def test_binding_desligado_ou_de_outra_fonte_nao_arma(self):
        for b in ({"source": "agent-hook", "autoResume": False},
                  {"source": "cli", "autoResume": True},
                  {"source": "cli", "autoResume": False}):
            self.assertIsNone(motivo_armado({"resumeBinding": b}), b)

    def test_terminal_vazio_nao_arma(self):
        self.assertIsNone(motivo_armado({}))
        self.assertIsNone(motivo_armado({"agent": None, "resumeBinding": None}))


class TestLerAutosave(unittest.TestCase):
    def setUp(self):
        self.mtime, self.p = ler_autosave(FIX_AUTOSAVE)

    def test_indexa_por_surface_em_maiusculas_e_so_terminais(self):
        self.assertEqual(sorted(self.p), sorted(U(n) for n in (1, 2, 3, 4, 5, 6, 8)))

    def test_carrega_janela_workspace_e_sessao(self):
        p = self.p[U(1)]
        self.assertEqual((p.janela, p.workspace, p.sessao),
                         ("A1000000-0000-4000-8000-000000000001",
                          "A2000000-0000-4000-8000-000000000001", S(1)))
        self.assertEqual(p.cwd, "/tmp/projeto-1111")

    def test_sessao_vem_do_binding_quando_nao_ha_agent(self):
        self.assertEqual(self.p[U(3)].sessao, S(3))
        self.assertIsNone(self.p[U(4)].sessao)

    def test_classifica_armadas(self):
        armadas = {u: p.armado for u, p in self.p.items() if p.armado}
        self.assertEqual(armadas, {U(1): "agent", U(2): "agent", U(3): "binding agent-hook",
                                   U(8): "agent"})

    def test_mtime_e_o_do_arquivo(self):
        self.assertEqual(self.mtime, os.stat(FIX_AUTOSAVE).st_mtime)

    def test_arquivo_ausente_ou_invalido_e_erro(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                ler_autosave(pathlib.Path(tmp) / "nao-existe.json")
            ruim = pathlib.Path(tmp) / "ruim.json"
            ruim.write_text("{")
            with self.assertRaises(RuntimeError):
                ler_autosave(ruim)
            ruim.write_text(json.dumps({"windows": "x"}))
            with self.assertRaises(RuntimeError):
                ler_autosave(ruim)


class TestLerHooks(unittest.TestCase):
    def test_indexa_por_sessao(self):
        h = ler_hooks(FIX_HOOKS)
        self.assertEqual(h[S(2)]["runtimeStatus"], "running")

    def test_ausente_ou_invalido_e_vazio(self):
        """O registro dos hooks e' sinal auxiliar: sem ele, a ociosidade sai do transcript."""
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(ler_hooks(pathlib.Path(tmp) / "nao-existe.json"), {})
            ruim = pathlib.Path(tmp) / "ruim.json"
            ruim.write_text("[")
            self.assertEqual(ler_hooks(ruim), {})


if __name__ == "__main__":
    unittest.main()
