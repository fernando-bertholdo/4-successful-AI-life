"""Um cmux falso: arvore, processos, autosave em arquivo e os dois jeitos de desarmar.

Reproduz o que foi medido no cmux 0.65.2 (TECH-1307): o SIGTERM no claude dispara o
SessionEnd, que tira agent e binding do autosave, e o app regrava o arquivo. Com
`session_end_limpa=False` e `rpc_limpa=False`, ele responde OK e nada muda: e' o caso
de 31/10/2026, em que o "OK" do CLI nao valia nada.

O app regrava o autosave a cada 8 s de relogio falso (o timer dele), salvo com
`autosave_parado=True`. Cada pid nasce no instante 500 + pid; `filhos` poe um claude
aninhado na aba (pai = o claude principal), e `filho_sobrevive` o deixa vivo depois do
SIGTERM no principal.
"""
import contextlib
import json
import os
import pathlib
import signal
import time
from unittest import mock

from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace, anexar_transcript

JANELA, WS = "A1000000-0000-4000-8000-000000000001", "A2000000-0000-4000-8000-000000000001"


def uuid(n):
    return "C%07d-0000-4000-8000-%012d" % (n, n)


def sessao(n):
    return "%08d-1111-4111-8111-%012d" % (n, n)


class CmuxFalso:
    """abas: lista de dicts {n, pid?, armada?, idade_transcript?}. n=1 e' a de controle."""

    def __init__(self, tmp, abas, session_end_limpa=True, rpc_limpa=True, nao_sai=(),
                 autosave_parado=False, filho_sobrevive=False, versao="cmux 0.65.2 (falso)",
                 extra_ps=(), fora_da_arvore=(), rearmar=(), some=(), reusa_pid=()):
        self.tmp = pathlib.Path(tmp)
        self.abas = abas
        self.session_end_limpa, self.rpc_limpa = session_end_limpa, rpc_limpa
        self.nao_sai = set(nao_sai)
        self.autosave_parado, self.filho_sobrevive = autosave_parado, filho_sobrevive
        self.versao, self.extra_ps = versao, list(extra_ps)
        self.vivos = {a["pid"]: a["n"] for a in abas if a.get("pid")}
        self.pais = {pid: str(9000 + n) for pid, n in self.vivos.items()}
        for a in abas:
            for filho in a.get("filhos", ()):
                self.vivos[filho] = a["n"]
                self.pais[filho] = a["pid"]
        self.desde_save = 0.0
        self.fora_da_arvore, self.rearmar = set(fora_da_arvore), set(rearmar)
        self.some, self.reusa_pid = set(some), set(reusa_pid)
        self.sinais, self.rpcs = [], []
        self.autosave = self.tmp / "autosave.json"
        self.hooks = self.tmp / "hooks.json"
        self.hooks.write_text(json.dumps({"sessions": {}}))
        self.raiz = self.tmp / "projetos"
        (self.raiz / "proj").mkdir(parents=True, exist_ok=True)
        agora = time.time()
        for a in abas:
            t = self.raiz / "proj" / (sessao(a["n"]) + ".jsonl")
            t.write_text('{"cwd": "/tmp/proj-%d"}\n' % a["n"])
            idade = a.get("idade_transcript", 3600)
            os.utime(t, (agora - idade, agora - idade))
        self.paineis = {uuid(a["n"]): self._terminal(a) for a in abas}
        self._gravar(agora - 120)

    def _terminal(self, a):
        if not a.get("armada", True):
            return {}
        s = sessao(a["n"])
        return {"agent": {"kind": "claude", "sessionId": s, "workingDirectory": "/tmp/p"},
                "resumeBinding": {"source": "agent-hook", "autoResume": True,
                                  "checkpointId": s, "kind": "claude"},
                "wasAgentRunning": bool(a.get("pid"))}

    def _gravar(self, mtime=None):
        if mtime is None:
            for n in self.rearmar:
                self.paineis[uuid(n)] = self._terminal({"n": n})
            for n in self.some:
                self.paineis.pop(uuid(n), None)
        panels = [{"id": u, "type": "terminal", "title": "aba", "terminal": t}
                  for u, t in self.paineis.items()]
        dados = {"windows": [{"windowId": JANELA, "tabManager": {"workspaces": [
            {"workspaceId": WS, "panels": panels}]}}]}
        self.autosave.write_text(json.dumps(dados))
        t = time.time() + 1 if mtime is None else mtime
        os.utime(self.autosave, (t, t))

    def _desarmar(self, surface):
        self.paineis[surface] = {}
        self._gravar()

    def estado(self):
        abas = []
        for a in self.abas:
            if a["n"] in self.fora_da_arvore:
                continue
            vivo = a.get("pid") in self.vivos
            abas.append(Aba(uuid=uuid(a["n"]), ref="surface:%d" % a["n"], tipo="terminal",
                            titulo="aba %d" % a["n"], sessao=sessao(a["n"]) if vivo else None,
                            cwd="/tmp/proj-%d" % a["n"] if vivo else None,
                            fonte="processo" if vivo else None,
                            pid=a["pid"] if vivo else None))
        for a in abas:
            if a.sessao:
                anexar_transcript(a, self.raiz)
        return Estado(janelas=[Janela(uuid=JANELA, ref="window:1", workspaces=[
            Workspace(uuid=WS, ref="workspace:1", nome="projeto",
                      panes=[Pane(uuid="P", ref="pane:1", abas=abas)])])])

    def kill(self, pid, sinal):
        pid = str(pid)
        if pid not in self.vivos:
            raise ProcessLookupError
        if sinal == 0:
            return
        self.sinais.append((pid, sinal))
        if sinal == signal.SIGTERM and pid not in self.nao_sai:
            n = self.vivos.pop(pid)
            if not self.filho_sobrevive:
                for filho in [p for p, pai in self.pais.items() if pai == pid]:
                    self.vivos.pop(filho, None)
            if self.session_end_limpa:
                self._desarmar(uuid(n))

    def tick(self, segundos):
        """O timer do app: regrava o autosave a cada 8 s, mesmo sem mudanca."""
        self.desde_save += segundos
        if self.desde_save >= 8 and not self.autosave_parado:
            self.desde_save = 0.0
            self._gravar()

    def args_de(self, pid):
        n = self.vivos.get(str(pid))
        if n is None:
            return ""
        if self.pais.get(str(pid)) in self.vivos:
            return "/Users/x/.local/bin/claude -p tarefa-aninhada"
        return "/Users/x/.local/bin/claude --resume %s" % sessao(n)

    def env_de(self, pid):
        args = self.args_de(pid)
        return args and "%s CMUX_SURFACE_ID=%s" % (args, uuid(self.vivos[str(pid)]))

    def inicio_de(self, pid):
        """O que o processo_confere le na hora do sinal; reusa_pid simula outro processo."""
        if str(pid) not in self.vivos:
            return None
        return 500.0 + int(pid) + (1 if str(pid) in self.reusa_pid else 0)

    def inicios_de(self, pids):
        """A leitura inicial."""
        return {p: 500.0 + int(p) for p in pids if str(p) in self.vivos}

    def ps_eww(self):
        linhas = ["%s %s" % (p, self.env_de(p)) for p in sorted(self.vivos, key=int)]
        return "\n".join(linhas + self.extra_ps)

    def rodar(self, *args):
        if args[:2] == ("rpc", "surface.resume.clear"):
            payload = json.loads(args[2])
            self.rpcs.append(payload)
            if self.rpc_limpa:
                self._desarmar(payload["surface_id"])
            return "OK"
        raise AssertionError("chamada inesperada ao cmux: %r" % (args,))

    @contextlib.contextmanager
    def ligado(self, modulo, protegidos=()):
        """Troca no modulo do script as fontes do sistema por este cmux falso."""
        from lib import autosave, cmux_state, encerrar
        relogio = [1000.0]
        eu = self

        class Tempo:
            @staticmethod
            def monotonic():
                return relogio[0]

            @staticmethod
            def sleep(s):
                relogio[0] += s
                eu.tick(s)

            time = staticmethod(time.time)

        with contextlib.ExitStack() as pilha:
            for troca in (mock.patch.object(modulo, "ler_estado", self.estado),
                          mock.patch.object(autosave, "CAMINHO_AUTOSAVE", self.autosave),
                          mock.patch.object(autosave, "CAMINHO_HOOKS", self.hooks),
                          mock.patch.object(cmux_state, "RAIZ_PROJETOS", self.raiz),
                          mock.patch.object(encerrar, "rodar_cmux", self.rodar),
                          mock.patch.object(encerrar, "_env_de", self.env_de),
                          mock.patch.object(encerrar, "_args_de", self.args_de),
                          mock.patch.object(encerrar, "_inicio_de", self.inicio_de),
                          mock.patch.object(cmux_state, "_ppid", self.pais.get),
                          mock.patch.object(encerrar, "time", Tempo),
                          mock.patch("os.kill", self.kill)):
                pilha.enter_context(troca)
            if hasattr(modulo, "ancestrais"):
                pilha.enter_context(mock.patch.object(modulo, "ancestrais",
                                                      lambda: set(protegidos)))
            if hasattr(modulo, "_ps_eww"):
                pilha.enter_context(mock.patch.object(modulo, "_ps_eww", self.ps_eww))
            if hasattr(modulo, "inicios_de"):
                pilha.enter_context(mock.patch.object(modulo, "inicios_de", self.inicios_de))
            if hasattr(modulo, "versao_do_cmux"):
                pilha.enter_context(mock.patch.object(modulo, "versao_do_cmux",
                                                      lambda: self.versao))
            yield self
