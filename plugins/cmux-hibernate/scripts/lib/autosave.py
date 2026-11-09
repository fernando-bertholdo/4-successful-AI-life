"""Le o que o cmux usa para decidir quem sobe sozinho ao reabrir.

A restauracao do cmux (medido na 0.65.2, TECH-1307) nao le o `resumeBinding` pelo
CLI: le o arquivo de sessao que o app regrava sozinho (autosave), painel a painel.
Um painel de terminal sobe com o Claude por dois caminhos:

- `terminal.agent`, o snapshot do agente, que basta para lancar o
  `cmux restore claude <sessao>` enquanto o binding for `agent-hook` ou nao existir;
- `terminal.resumeBinding` com `source: agent-hook` e `autoResume: true`.

O `wasAgentRunning` gravado ali nao entra na regra: o save do fechamento o recalcula
com os processos daquele instante, e um `claude` vivo no Cmd+Q o torna `true`. Por
isso `agent` presente ja conta como armada.

O app regrava o arquivo de 1 a 4 s depois de uma mudanca (timer de 8 s; sem mudanca,
o save pode ser pulado por ate' 60 s).
"""
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

CAMINHO_AUTOSAVE = (Path.home() / "Library" / "Application Support" / "cmux"
                    / "session-com.cmuxterm.app.json")
CAMINHO_HOOKS = Path.home() / ".cmuxterm" / "claude-hook-sessions.json"
VERSAO_MEDIDA = "0.65.2"  # a versao do cmux em que esta mecanica foi lida e medida


@dataclass
class Painel:
    surface: str
    janela: str
    workspace: str
    sessao: Optional[str]
    cwd: Optional[str]
    armado: Optional[str]
    titulo: str = ""


def motivo_armado(terminal: dict) -> Optional[str]:
    """Por que o painel sobe sozinho no proximo restore; None quando nao sobe."""
    if terminal.get("agent"):
        return "agent"
    b = terminal.get("resumeBinding") or {}
    if b.get("source") == "agent-hook" and b.get("autoResume") is True:
        return "binding agent-hook"
    return None


def _painel(janela: str, workspace: str, p: dict) -> Optional[Painel]:
    t = p.get("terminal")
    if p.get("type") != "terminal" or not isinstance(t, dict) or not p.get("id"):
        return None
    a = t.get("agent") or {}
    b = t.get("resumeBinding") or {}
    return Painel(surface=p["id"].upper(), janela=janela, workspace=workspace,
                  sessao=a.get("sessionId") or b.get("checkpointId"),
                  cwd=a.get("workingDirectory") or b.get("cwd"),
                  armado=motivo_armado(t), titulo=p.get("title") or "")


def paineis(dados: dict) -> Dict[str, Painel]:
    """surface (uuid em maiusculas, o formato do CMUX_SURFACE_ID) -> Painel."""
    achados: Dict[str, Painel] = {}
    for j in dados["windows"]:
        for w in j["tabManager"]["workspaces"]:
            for p in w.get("panels", []):
                painel = _painel(j["windowId"], w["workspaceId"], p)
                if painel:
                    achados[painel.surface] = painel
    return achados


def ler_autosave(caminho: Optional[Path] = None) -> Tuple[float, Dict[str, Painel]]:
    """(mtime, paineis). Erro de leitura ou de formato e' RuntimeError: sem esta fonte
    nao ha como conferir desarme nenhum."""
    caminho = caminho or CAMINHO_AUTOSAVE
    try:
        mtime = caminho.stat().st_mtime
        return mtime, paineis(json.loads(caminho.read_text()))
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as e:
        raise RuntimeError("nao li o autosave do cmux em %s (%s)" % (caminho, e))


def ler_hooks(caminho: Optional[Path] = None) -> Dict[str, dict]:
    """sessao -> ultimo registro do hook do Claude no cmux; {} quando nao da para ler."""
    caminho = caminho or CAMINHO_HOOKS
    try:
        dados = json.loads(caminho.read_text())
        return {k: v for k, v in dados["sessions"].items() if isinstance(v, dict)}
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return {}
