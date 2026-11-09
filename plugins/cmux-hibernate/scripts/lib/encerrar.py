"""Desarma de verdade: encerra o claude ocioso da aba e confere no autosave do cmux.

Por que encerrar, e nao reescrever o binding (medido no cmux 0.65.2, TECH-1307):
- `cmux surface resume set --source agent-hook` sem `auto_resume: true` e' recusado
  quando a aba ja tem um binding `agent-hook` confiavel, e o CLI imprime `OK` mesmo
  assim. Foi o que deixou 11 abas subirem sozinhas em 31/10/2026;
- quando o `claude` sai, o hook `SessionEnd` tira do autosave o `agent` e o binding
  da aba, e a memoria sai junto.

Para aba armada sem processo (o restore dela falhou, por exemplo), a reserva e'
`cmux rpc surface.resume.clear` com `agent_session_ended: true`. Esse parametro e'
contrato interno do hook do cmux, nao aparece no `--help`: por isso e' so' reserva,
e o resultado so' vale conferido no autosave.
"""
import json
import os
import re
import signal
import subprocess
import time
from typing import Callable, Dict, Iterable, List, Optional, Set

from lib.autosave import ler_autosave
from lib.cmux_state import inicios_de, rodar_cmux

JANELA_OCUPADA = 60   # s: transcript escrito ha menos que isso = sessao em turno
TETO_SAIDA = 10.0     # s para o claude sair depois do SIGTERM
TETO_CONFERENCIA = 20.0  # s para o cmux regravar o autosave (o timer dele e' de 8 s)
TETO_SEM_MUDANCA = 75.0  # s: sem mudanca, o cmux pode pular o save por ate' 60 s
_STATUS_OCUPADO = {"running", "needsInput"}
_CICLO_OCUPADO = {"running", "needsInput", "backgroundWorkPending"}


def _registros(sessao: str, surface: Optional[str], hooks: Dict[str, dict]) -> List[dict]:
    """O registro da sessao e os de qualquer sessao que o hook ligue a mesma aba."""
    regs = [hooks[sessao]] if sessao in hooks else []
    if surface:
        regs += [r for k, r in hooks.items() if k != sessao
                 and str(r.get("surfaceId") or "").upper() == surface.upper()]
    return regs


def motivo_ocupada(sessao: str, transcript_mtime, hooks: Dict[str, dict], agora: float,
                   janela: int = JANELA_OCUPADA, surface: Optional[str] = None) -> Optional[str]:
    """Por que nao encerrar agora; None quando a sessao esta ociosa.

    Dois sinais baratos, e basta um. O transcript `.jsonl` escrito nos ultimos `janela`
    segundos: o da sessao e o mais recente do mesmo projeto, porque depois de um /clear a
    aba escreve noutro arquivo (`transcript_mtime` aceita um numero ou uma lista). E o
    registro do hook do cmux, achado pela sessao ou pela aba, dizendo que ha turno, pedido
    de permissao ou trabalho de fundo (subagente). O transcript nao e' escrito durante uma
    ferramenta longa; o registro do hook cobre esse caso quando existe. `error` so' conta
    se for recente: senao uma aba que errou uma vez ficaria pulada para sempre."""
    mtimes = (transcript_mtime if isinstance(transcript_mtime, (list, tuple))
              else [transcript_mtime])
    mtimes = [m for m in mtimes if m is not None]
    if mtimes and agora - max(mtimes) < janela:
        return "transcript escrito ha %d s" % max(0, int(agora - max(mtimes)))
    for reg in _registros(sessao, surface, hooks):
        status, ciclo = reg.get("runtimeStatus"), reg.get("agentLifecycle")
        if status in _STATUS_OCUPADO:
            return "hook do cmux diz %s" % status
        if ciclo in _CICLO_OCUPADO:
            return "hook do cmux diz %s" % ciclo
        if status == "error" and agora - float(reg.get("updatedAt") or 0) < janela:
            return "hook do cmux diz error ha menos de %d s" % janela
    return None


def _ppid(pid: str) -> Optional[str]:
    r = subprocess.run(["ps", "-o", "ppid=", "-p", pid], capture_output=True, text=True)
    saida = r.stdout.strip()
    return saida or None


def ancestrais(pid: Optional[str] = None,
               ppid: Optional[Callable[[str], Optional[str]]] = None) -> Set[str]:
    """O pid e toda a cadeia de pais. Encerrar um deles mataria quem roda o comando."""
    ppid = ppid or _ppid
    atual = pid or str(os.getpid())
    vistos: Set[str] = set()
    while atual and atual != "0" and atual not in vistos:
        vistos.add(atual)
        atual = ppid(atual)
    return vistos


def _env_de(pid: str) -> str:
    r = subprocess.run(["ps", "eww", "-o", "command=", "-p", pid],
                       capture_output=True, text=True)
    return r.stdout.replace("\n", " ")


def _args_de(pid: str) -> str:
    r = subprocess.run(["ps", "-o", "args=", "-p", pid], capture_output=True, text=True)
    return r.stdout.strip()


def _inicio_de(pid: str) -> Optional[float]:
    return inicios_de([pid]).get(pid)


_RE_SURFACE = re.compile(r"(?:^|\s)CMUX_SURFACE_ID=([0-9A-Fa-f-]{36})(?:\s|$)")


def processo_confere(pid: str, surface: str, inicio: Optional[float] = None,
                     args_de: Optional[Callable[[str], str]] = None,
                     env_de: Optional[Callable[[str], str]] = None,
                     inicio_de: Optional[Callable[[str], Optional[float]]] = None) -> bool:
    """O pid ainda e' o claude daquela aba? Relido logo antes do SIGTERM.

    O binario vem do argv (`ps -o args=`), nao da linha com o ambiente, onde um caminho
    no PATH passaria por claude; o daemon de fundo nao conta. A aba vem da variavel
    `CMUX_SURFACE_ID` com o nome exato e o uuid inteiro. Com `inicio`, o instante em que
    o processo nasceu tem de ser o da leitura inicial: e' o que barra pid reusado."""
    args = (args_de or _args_de)(pid)
    if "/.local/bin/claude" not in args.split(" ", 1)[0] or " daemon run" in " " + args:
        return False
    m = _RE_SURFACE.search((env_de or _env_de)(pid))
    if not m or m.group(1).upper() != surface.upper():
        return False
    if inicio is not None and (inicio_de or _inicio_de)(pid) != inicio:
        return False
    return True


def _vivo(pid: str) -> bool:
    try:
        os.kill(int(pid), 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def encerrar(pids: Iterable[str], matar=None, vivo=None, dormir=None, relogio=None,
             teto: float = TETO_SAIDA) -> Set[str]:
    """SIGTERM em cada pid e espera ate' o teto. Devolve os que nao sairam. Nunca SIGKILL."""
    matar, vivo = matar or os.kill, vivo or _vivo
    dormir, relogio = dormir or time.sleep, relogio or time.monotonic
    pendentes = set()
    for pid in pids:
        try:
            matar(int(pid), signal.SIGTERM)
        except ProcessLookupError:
            continue
        pendentes.add(pid)
    limite = relogio() + teto
    while pendentes:
        pendentes = {p for p in pendentes if vivo(p)}
        if not pendentes or relogio() >= limite:
            break
        dormir(0.2)
    return pendentes


def limpar_registro(painel, rodar=None) -> str:
    """Pede ao cmux que esqueca o agente da aba. A resposta nao prova nada: confira."""
    payload = {"window_id": painel.janela, "workspace_id": painel.workspace,
               "surface_id": painel.surface, "checkpoint_id": painel.sessao,
               "source": "agent-hook", "agent_session_ended": True}
    return (rodar or rodar_cmux)("rpc", "surface.resume.clear", json.dumps(payload))


def conferir(surfaces: Iterable[str], depois_de: float, ler=None, dormir=None, relogio=None,
             teto: float = TETO_CONFERENCIA,
             iniciais: Optional[Iterable[str]] = None) -> Dict[str, Optional[str]]:
    """surface -> None (desarmada no autosave regravado depois de `depois_de`) ou o motivo
    da falha. So' vale um save posterior a acao; le de novo ate' o teto. Painel que estava
    em `iniciais` e sumiu, ou um autosave sem nenhum painel de terminal, nao confere: o
    cmux pode estar no meio de uma regravacao, e ausencia nao e' prova de desarme."""
    iniciais = {s.upper() for s in (iniciais or ())}
    ler, dormir = ler or ler_autosave, dormir or time.sleep
    relogio = relogio or time.monotonic
    alvos = [s.upper() for s in surfaces]
    if not alvos:
        return {}
    limite = relogio() + teto
    falha = {s: "o cmux nao regravou o autosave em %d s" % teto for s in alvos}
    while True:
        try:
            mtime, paineis = ler()
        except RuntimeError as e:
            falha = {s: str(e) for s in alvos}
        else:
            if mtime > depois_de:
                falha = {}
                for s in alvos:
                    p = paineis.get(s)
                    if not paineis:
                        falha[s] = "o autosave nao tem paineis de terminal"
                    elif p is None and s in iniciais:
                        falha[s] = "o painel sumiu do autosave"
                    elif p is not None and p.armado:
                        falha[s] = "continua armada (%s)" % p.armado
                if not falha:
                    return {s: None for s in alvos}
        if relogio() >= limite:
            return {s: falha.get(s) for s in alvos}
        dormir(1.0)


def ler_fresco(depois_de: float, ler=None, dormir=None, relogio=None,
               teto: float = TETO_SEM_MUDANCA):
    """(paineis, None) do primeiro autosave regravado depois de `depois_de`, ou
    (None, motivo). Sem mudanca nenhuma, o cmux pode levar ate' 60 s para regravar."""
    ler, dormir = ler or ler_autosave, dormir or time.sleep
    relogio = relogio or time.monotonic
    limite = relogio() + teto
    motivo = "o cmux nao regravou o autosave em %d s" % teto
    while True:
        try:
            mtime, paineis = ler()
        except RuntimeError as e:
            motivo = str(e)
        else:
            if mtime > depois_de:
                return paineis, None
        if relogio() >= limite:
            return None, motivo
        dormir(1.0)
