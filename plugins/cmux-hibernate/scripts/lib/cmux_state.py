"""Deriva o estado real do cmux cruzando processo, filesystem e CLI.

Hierarquia de confianca das fontes (do mais confiavel para o menos):

    CMUX_SURFACE_ID (ps eww)   -> vinculo sessao<->aba      FATO
    lsof -d cwd                -> diretorio do processo     FATO
    cmux tree                  -> estrutura e titulos       FATO
    cmux surface resume get    -> vinculo pretendido        INTENCAO

O binding do cmux registra a intencao gravada por um hook e envelhece quando uma
sessao passa a gravar sob outro id. Por isso ele entra por ultimo e apenas
preenche lacunas.
"""
from dataclasses import dataclass, field
from typing import Dict, Iterator, List, Optional, Tuple
import os
import re
import subprocess


@dataclass
class Aba:
    uuid: str
    ref: str
    tipo: str
    titulo: str
    sessao: Optional[str] = None
    cwd: Optional[str] = None
    fonte: Optional[str] = None
    transcript: Optional[dict] = None
    estagnada: bool = False
    url: Optional[str] = None


@dataclass
class Pane:
    uuid: str
    ref: str
    abas: List[Aba] = field(default_factory=list)


@dataclass
class Workspace:
    uuid: str
    ref: str
    nome: str
    panes: List[Pane] = field(default_factory=list)


@dataclass
class Janela:
    uuid: str
    ref: str
    workspaces: List[Workspace] = field(default_factory=list)


@dataclass
class Estado:
    janelas: List[Janela] = field(default_factory=list)

    def todas_abas(self) -> Iterator[Tuple[Janela, Workspace, Pane, Aba]]:
        for j in self.janelas:
            for w in j.workspaces:
                for p in w.panes:
                    for a in p.abas:
                        yield j, w, p, a


_RE_JANELA = re.compile(r"window (window:\d+) ([0-9A-F-]{36})")
_RE_WS = re.compile(r"workspace (workspace:\d+) ([0-9A-F-]{36}) \"([^\"]*)\"")
_RE_PANE = re.compile(r"pane (pane:\d+) ([0-9A-F-]{36})")
_RE_ABA = re.compile(r"surface (surface:\d+) ([0-9A-F-]{36}) \[(\w+)\] \"(.*?)\"(.*)$")
_RE_URL = re.compile(r"(https?://\S+)")


def parse_tree(texto: str) -> List[Janela]:
    """Converte a saida de `cmux tree --all --id-format both` em objetos."""
    janelas: List[Janela] = []
    janela = ws = pane = None
    for linha in texto.splitlines():
        m = _RE_JANELA.search(linha)
        if m:
            janela = Janela(ref=m.group(1), uuid=m.group(2))
            janelas.append(janela)
            ws = pane = None
            continue
        m = _RE_WS.search(linha)
        if m and janela is not None:
            ws = Workspace(ref=m.group(1), uuid=m.group(2), nome=m.group(3))
            janela.workspaces.append(ws)
            pane = None
            continue
        m = _RE_PANE.search(linha)
        if m and ws is not None:
            pane = Pane(ref=m.group(1), uuid=m.group(2))
            ws.panes.append(pane)
            continue
        m = _RE_ABA.search(linha)
        if m and pane is not None:
            resto = m.group(5)
            url = _RE_URL.search(resto)
            pane.abas.append(Aba(
                ref=m.group(1),
                uuid=m.group(2),
                tipo=m.group(3),
                titulo=m.group(4),
                url=url.group(1) if url else None,
            ))
    return janelas


_RE_SESSAO = re.compile(r"--(?:resume|session-id)\s+([0-9a-f-]{36})")
_RE_SURFACE = re.compile(r"CMUX_SURFACE_ID=([0-9A-F-]{36})")


def parse_processos(saida_ps: str) -> Dict[str, dict]:
    """Mapeia surface_uuid -> {sessao, pid} a partir de `ps eww` com env anexado.

    Ignora processos auxiliares (daemon, bg-pty-host, bg-spare): eles herdam
    CMUX_SURFACE_ID e roubariam a aba da sessao real.
    """
    mapa: Dict[str, dict] = {}
    for linha in saida_ps.splitlines():
        if "/.local/bin/claude" not in linha:
            continue
        if " daemon run" in linha or "bg-pty-host" in linha or "bg-spare" in linha:
            continue
        m_sess = _RE_SESSAO.search(linha)
        m_surf = _RE_SURFACE.search(linha)
        if not (m_sess and m_surf):
            continue
        mapa[m_surf.group(1)] = {"sessao": m_sess.group(1), "pid": linha.split()[0]}
    return mapa


def resolver_cwd(pid: str) -> Optional[str]:
    """Diretorio real do processo, com o symlink ja resolvido pelo kernel."""
    try:
        saida = subprocess.run(
            ["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for linha in saida.splitlines():
        if linha.startswith("n"):
            return os.path.realpath(linha[1:])
    return None


def aplicar_processos(estado: Estado, mapa: Dict[str, dict], cwds: Dict[str, str]) -> None:
    """Sobrescreve o vinculo com o que o processo diz. Fato vence intencao."""
    for *_, aba in estado.todas_abas():
        info = mapa.get(aba.uuid)
        if not info:
            continue
        aba.sessao = info["sessao"]
        aba.fonte = "processo"
        cwd = cwds.get(info["pid"])
        if cwd:
            aba.cwd = cwd


def detectar_duplicatas(mapa: Dict[str, dict]) -> List[str]:
    """Sessoes presentes em mais de uma aba — estado anomalo.

    Nao desarmar nem subir essas: escrever binding em duas abas para a mesma
    sessao produziria instancias competindo pelo mesmo transcript.
    """
    contagem: Dict[str, int] = {}
    for info in mapa.values():
        contagem[info["sessao"]] = contagem.get(info["sessao"], 0) + 1
    return sorted(s for s, n in contagem.items() if n > 1)
