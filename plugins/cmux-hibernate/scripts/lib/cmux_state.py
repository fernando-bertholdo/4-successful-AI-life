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
from pathlib import Path
from typing import Dict, Iterator, List, Optional, Tuple
import json
import os
import re
import shutil
import subprocess
import time

STALE_DAYS = 7
RAIZ_PROJETOS = Path.home() / ".claude" / "projects"
RAIZ_SESSOES = Path.home() / ".claude" / "sessions"  # <pid>.json que o Claude Code grava


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
    pid: Optional[str] = None
    armada: Optional[str] = None


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
    # surface -> pid de todo claude com aba, tenha ou nao o id da sessao no argv
    processos: Dict[str, str] = field(default_factory=dict)

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


def surfaces_com_processo(saida_ps: str) -> Dict[str, str]:
    """surface_uuid -> pid de TODO processo claude com aba, tenha ou nao id no argv.

    O cmux retoma por titulo quando a sessao foi renomeada
    (`--resume meu-titulo` em vez de `--resume <uuid>`), e nesses casos o id
    nao aparece na linha de comando. Estes sao os candidatos a complemento
    pelo binding.
    """
    vivos: Dict[str, str] = {}
    for linha in saida_ps.splitlines():
        if "/.local/bin/claude" not in linha:
            continue
        if " daemon run" in linha or "bg-pty-host" in linha or "bg-spare" in linha:
            continue
        m_surf = _RE_SURFACE.search(linha)
        if m_surf:
            vivos[m_surf.group(1)] = linha.split()[0]
    return vivos


def _e_claude_de_aba(linha: str) -> bool:
    return ("/.local/bin/claude" in linha and " daemon run" not in linha
            and "bg-pty-host" not in linha and "bg-spare" not in linha)


def claudes_por_surface(saida_ps: str) -> Dict[str, List[str]]:
    """surface_uuid -> todos os pids de claude na aba, na ordem do ps."""
    por: Dict[str, List[str]] = {}
    for linha in saida_ps.splitlines():
        m = _RE_SURFACE.search(linha)
        if m and _e_claude_de_aba(linha):
            por.setdefault(m.group(1), []).append(linha.split()[0])
    return por


_MARCA_CMUX = "__CFBundleIdentifier=com.cmuxterm.app"


def _registro_do_claude(pid: str, raiz: Path) -> dict:
    """O `~/.claude/sessions/<pid>.json` que o Claude Code grava, se for deste pid."""
    try:
        dados = json.loads((raiz / ("%s.json" % pid)).read_text())
    except (OSError, ValueError):
        return {}
    return dados if isinstance(dados, dict) and str(dados.get("pid")) == pid else {}


def claudes_sem_aba(saida_ps: str, raiz_sessoes: Optional[Path] = None) -> List[dict]:
    """Claude vivo que descende do app cmux mas nao tem CMUX_SURFACE_ID.

    O plugin so' enxerga uma sessao pela variavel, entao esta fica fora do plano e do
    inventario; mesmo assim ela morre no Cmd+Q, junto com o terminal do cmux. A marca de
    "aberto no cmux" e' o __CFBundleIdentifier que o app passa aos filhos. O id da sessao
    sai do argv ou, sem ele, do registro do Claude Code por pid.
    """
    raiz = raiz_sessoes or RAIZ_SESSOES
    achados = []
    for linha in saida_ps.splitlines():
        if not _e_claude_de_aba(linha) or _RE_SURFACE.search(linha) or _MARCA_CMUX not in linha:
            continue
        pid = linha.split()[0]
        registro = _registro_do_claude(pid, raiz)
        m_sess = _RE_SESSAO.search(linha)
        achados.append({"pid": pid,
                        "sessao": m_sess.group(1) if m_sess else registro.get("sessionId"),
                        "cwd": registro.get("cwd")})
    return achados


def _ppid(pid: str) -> Optional[str]:
    r = subprocess.run(["ps", "-o", "ppid=", "-p", pid], capture_output=True, text=True)
    return r.stdout.strip() or None


def so_principais(saida_ps: str, ppid=None) -> str:
    """Tira do `ps` o claude aninhado (rodado por uma ferramenta de outro claude na mesma
    aba, que herda o CMUX_SURFACE_ID): fica o que nao descende de outro claude da aba.
    Sem como ler os pais, fica o primeiro."""
    ppid = ppid or _ppid
    descartar = set()
    for pids in claudes_por_surface(saida_ps).values():
        if len(pids) < 2:
            continue
        conjunto, principais = set(pids), []
        for pid in pids:
            atual, vistos, aninhado = ppid(pid), set(), False
            while atual and atual not in ("0", "1") and atual not in vistos:
                if atual in conjunto:
                    aninhado = True
                    break
                vistos.add(atual)
                atual = ppid(atual)
            if not aninhado:
                principais.append(pid)
        fica = (principais or pids)[0]
        descartar |= conjunto - {fica}
    return "\n".join(l for l in saida_ps.splitlines()
                     if not l.split() or l.split()[0] not in descartar)


def binding_de(janela: str, workspace: str, surface: str) -> Optional[dict]:
    """Le o resumeBinding de uma aba. Intencao, nao fato — usar so' como complemento."""
    try:
        dados = json.loads(rodar_cmux(
            "surface", "resume", "get", "--json",
            "--window", janela, "--workspace", workspace, "--surface", surface))
    except (ValueError, RuntimeError):
        return None
    b = dados.get("resume_binding")
    return b if b and b.get("kind") == "claude" else None


def complementar_por_binding(estado: Estado, vivos: Dict[str, str]) -> int:
    """Preenche abas que tem processo vivo mas cujo id nao apareceu no argv.

    Marca fonte='binding' para deixar explicito que o dado e' menos confiavel
    que o dos processos.
    """
    preenchidas = 0
    for janela, ws, _pane, aba in estado.todas_abas():
        if aba.sessao or aba.uuid not in vivos:
            continue
        b = binding_de(janela.uuid, ws.uuid, aba.uuid)
        if not b or not b.get("checkpoint_id"):
            continue
        aba.sessao = b["checkpoint_id"]
        aba.fonte = "binding"
        aba.pid = vivos[aba.uuid]
        if not aba.cwd:
            aba.cwd = resolver_cwd(vivos[aba.uuid]) or b.get("cwd")
        preenchidas += 1
    return preenchidas


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
        aba.pid = info["pid"]
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


def localizar_transcript(sessao: str, raiz: Path = RAIZ_PROJETOS) -> Optional[Path]:
    """Acha o .jsonl da sessao em qualquer slug de projeto.

    O slug do diretorio deriva do caminho e pode divergir do cwd atual depois de
    um symlink. Por isso a busca e' por session id, nunca por nome de projeto.
    """
    try:
        achados = sorted(raiz.glob("*/" + sessao + ".jsonl"),
                         key=lambda p: p.stat().st_mtime, reverse=True)
    except OSError:
        return None
    return achados[0] if achados else None


def cwd_do_transcript(caminho: Path) -> Optional[str]:
    """Le o cwd gravado dentro do transcript — a fonte que nao mente."""
    try:
        with caminho.open(errors="ignore") as fh:
            for i, linha in enumerate(fh):
                if i > 40:
                    break
                try:
                    obj = json.loads(linha)
                except ValueError:
                    continue
                if obj.get("cwd"):
                    return obj["cwd"]
    except OSError:
        return None
    return None


def anexar_transcript(aba: Aba, raiz: Path = RAIZ_PROJETOS) -> None:
    caminho = localizar_transcript(aba.sessao, raiz)
    if caminho:
        st = caminho.stat()
        aba.transcript = {"path": str(caminho), "kb": st.st_size // 1024,
                          "mtime": st.st_mtime}
        if not aba.cwd:
            aba.cwd = cwd_do_transcript(caminho)


def marcar_estagnadas(estado: Estado, agora: float, stale_days: int = STALE_DAYS) -> None:
    limite = agora - stale_days * 86400
    for *_, aba in estado.todas_abas():
        if aba.transcript and aba.transcript.get("mtime", 0) < limite:
            aba.estagnada = True


def cmux_bin() -> str:
    do_env = os.environ.get("CMUX_BUNDLED_CLI_PATH")
    if do_env and os.path.exists(do_env):
        return do_env
    padrao = "/Applications/cmux.app/Contents/Resources/bin/cmux"
    if os.path.exists(padrao):
        return padrao
    achado = shutil.which("cmux")
    if not achado:
        raise RuntimeError("cmux nao encontrado: abra o cmux ou defina CMUX_BUNDLED_CLI_PATH")
    return achado


def rodar_cmux(*args: str) -> str:
    env = dict(os.environ, CMUX_QUIET="1")
    r = subprocess.run([cmux_bin(), *args], capture_output=True, text=True,
                       env=env, timeout=30)
    return r.stdout


def _lstart(campos: List[str]) -> Optional[float]:
    """`ps -o lstart` (LC_ALL=C) em hora local do host -> epoch."""
    try:
        return time.mktime(time.strptime(" ".join(campos), "%a %b %d %H:%M:%S %Y"))
    except (ValueError, OverflowError):
        return None


def _inicios_de_ps(saida: str) -> Dict[str, float]:
    inicios: Dict[str, float] = {}
    for linha in saida.splitlines():
        campos = linha.split()
        if len(campos) >= 6 and campos[0].isdigit():
            t = _lstart(campos[1:6])
            if t is not None:
                inicios[campos[0]] = t
    return inicios


def _inicio_do_cmux_de_ps(saida: str) -> Optional[float]:
    for linha in saida.splitlines():
        campos = linha.split()
        if len(campos) >= 7 and campos[6].endswith(".app/Contents/MacOS/cmux"):
            return _lstart(campos[1:6])
    return None


def _ps(*args: str) -> str:
    env = dict(os.environ, LC_ALL="C")
    return subprocess.run(["ps", *args], capture_output=True, text=True, env=env).stdout


def inicios_de(pids: List[str]) -> Dict[str, float]:
    """pid -> instante em que o processo nasceu (epoch)."""
    if not pids:
        return {}
    return _inicios_de_ps(_ps("-o", "pid=,lstart=", "-p", ",".join(pids)))


def inicio_do_cmux() -> Optional[float]:
    """Quando o app do cmux que esta aberto nasceu; None se nao esta aberto."""
    return _inicio_do_cmux_de_ps(_ps("-A", "-ww", "-o", "pid=,lstart=,command="))


def versao_do_cmux() -> Optional[str]:
    try:
        return rodar_cmux("--version").strip() or None
    except (RuntimeError, OSError, subprocess.SubprocessError):
        return None


def _ps_eww() -> str:
    """Uma linha por processo claude, com o environment anexado."""
    base = subprocess.run(["ps", "-A", "-ww", "-o", "pid=,command="],
                          capture_output=True, text=True).stdout
    linhas = []
    for linha in base.splitlines():
        if "/.local/bin/claude" not in linha or " daemon run" in linha:
            continue
        if "grep " in linha:
            continue
        pid = linha.split()[0]
        env = subprocess.run(["ps", "eww", "-o", "command=", "-p", pid],
                             capture_output=True, text=True).stdout.replace("\n", " ")
        linhas.append(pid + " " + env)
    return "\n".join(linhas)


def ler_estado(raiz_projetos: Path = RAIZ_PROJETOS) -> Estado:
    """Estado real agora: estrutura do cmux + vinculos vindos dos processos."""
    estado = Estado(janelas=parse_tree(rodar_cmux("tree", "--all", "--id-format", "both")))
    saida_ps = so_principais(_ps_eww())
    mapa = parse_processos(saida_ps)

    cwds: Dict[str, str] = {}
    for info in mapa.values():
        cwd = resolver_cwd(info["pid"])
        if cwd:
            cwds[info["pid"]] = cwd
    aplicar_processos(estado, mapa, cwds)

    # Abas com processo vivo cujo id nao apareceu no argv (retomadas por titulo):
    # o binding e' o unico caminho, e fica marcado como tal.
    estado.processos = surfaces_com_processo(saida_ps)
    complementar_por_binding(estado, estado.processos)

    for *_, aba in estado.todas_abas():
        if aba.sessao:
            anexar_transcript(aba, raiz_projetos)

    marcar_estagnadas(estado, agora=time.time())
    return estado
