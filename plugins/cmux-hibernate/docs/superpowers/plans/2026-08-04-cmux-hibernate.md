# cmux-hibernate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir fechar o cmux por vontade própria e reabrir com o ambiente intacto e leve — abas armadas, sessões dormindo.

**Architecture:** Dois executáveis Python (`hibernate.py`, `wake.py`) sobre um núcleo compartilhado (`lib/cmux_state.py`) que deriva o estado real cruzando `ps eww`, `lsof`, `cmux tree` e os transcripts. A skill é um invólucro fino. Nenhuma decisão do fluxo depende de julgamento de LLM.

**Tech Stack:** Python 3.9+ (somente stdlib), `unittest`, bash para o runner de testes, CLI do cmux (`cmux tree`, `cmux surface resume`, `cmux rpc`).

## Global Constraints

- **Somente stdlib.** Nenhuma dependência externa (`subprocess`, `json`, `re`, `os`, `pathlib`, `dataclasses`, `datetime`, `argparse`). O plugin precisa rodar em qualquer máquina sem `pip install`.
- **Python 3.9+.** Não usar sintaxe de união `X | None` em anotações avaliadas; usar `Optional[X]` de `typing`.
- **Fonte primária é o processo.** `CMUX_SURFACE_ID` (via `ps eww`) e `lsof -d cwd` são fato. `cmux surface resume get` é intenção e só preenche lacunas. Todo campo derivado do binding carrega `fonte="binding"`.
- **Anti-duplicação por `session_id`.** Nunca por título, índice ou posição.
- **Nada de mutação sem intenção explícita.** `hibernate.py` só muta com `--apply`; o padrão é dry-run.
- **Caminho de estado:** `~/.local/state/cmux-hibernate/<ISO>/`. Retenção: 5 snapshots.
- **`STALE_DAYS` = 7** (qualifica sessões). **`MAX_SNAPSHOT_AGE` = 3** (qualifica snapshots). Parâmetros distintos.
- **Binário do cmux:** resolver de `CMUX_BUNDLED_CLI_PATH`, senão `/Applications/cmux.app/Contents/Resources/bin/cmux`, senão `cmux` do PATH. Sempre com `CMUX_QUIET=1`.
- **Mensagens ao usuário em português.** Nomes de código, identificadores e commits em inglês técnico onde já é convenção do repo; corpo de commit em pt-BR.

---

### Task 1: Esqueleto do plugin e fixtures reais

**Files:**
- Create: `plugins/cmux-hibernate/.claude-plugin/plugin.json`
- Create: `plugins/cmux-hibernate/scripts/lib/__init__.py`
- Create: `plugins/cmux-hibernate/tests/run-tests.sh`
- Create: `plugins/cmux-hibernate/tests/fixtures/capture.sh`
- Create: `plugins/cmux-hibernate/tests/fixtures/tree.txt`
- Create: `plugins/cmux-hibernate/tests/fixtures/ps-eww.txt`
- Create: `plugins/cmux-hibernate/tests/fixtures/README.md`

**Interfaces:**
- Consumes: nada.
- Produces: fixtures em disco que todas as tasks seguintes usam; `tests/run-tests.sh` como runner único.

- [ ] **Step 1: Criar o manifesto do plugin**

```json
{
  "name": "cmux-hibernate",
  "version": "0.1.0",
  "description": "Hibernate and restore Claude Code sessions across cmux workspaces, freeing memory without losing your environment",
  "author": { "name": "Fernando Bertholdo", "url": "https://github.com/fernando-bertholdo" },
  "repository": "https://github.com/fernando-bertholdo/4-successful-AI-life",
  "license": "MIT",
  "keywords": ["cmux", "session", "restore", "hibernate", "memory", "workspace"],
  "skills": "./skills/"
}
```

- [ ] **Step 2: Criar o script de captura de fixtures**

`tests/fixtures/capture.sh` — grava o estado real para virar fixture. Roda uma vez, com o cmux cheio.

```bash
#!/usr/bin/env bash
# Captura saidas reais do ambiente para servirem de fixture nos testes.
# Rode com o cmux aberto e varias sessoes ativas.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
CMUX="${CMUX_BUNDLED_CLI_PATH:-/Applications/cmux.app/Contents/Resources/bin/cmux}"

CMUX_QUIET=1 "$CMUX" tree --all --id-format both > "$DIR/tree.txt"

# uma linha por processo claude: "<pid> <command...>" com o env anexado
: > "$DIR/ps-eww.txt"
ps -A -ww -o pid=,command= | grep "/.local/bin/claude" | grep -v " daemon run" | while read -r pid _; do
  ps eww -o command= -p "$pid" | tr '\n' ' ' | sed "s|^|$pid |" >> "$DIR/ps-eww.txt"
  printf '\n' >> "$DIR/ps-eww.txt"
done

echo "tree.txt   : $(wc -l < "$DIR/tree.txt") linhas"
echo "ps-eww.txt : $(wc -l < "$DIR/ps-eww.txt") processos"
```

- [ ] **Step 3: Capturar as fixtures**

Run:
```bash
chmod +x plugins/cmux-hibernate/tests/fixtures/capture.sh
plugins/cmux-hibernate/tests/fixtures/capture.sh
```
Expected: `tree.txt` com dezenas de linhas e `ps-eww.txt` com uma linha por sessão.

**Sanitização obrigatória:** as fixtures contêm caminhos e títulos reais. Revise `tree.txt` e `ps-eww.txt` e substitua qualquer título que exponha conteúdo sensível de trabalho por um genérico (`"projeto X: tarefa Y"`). Mantenha a **estrutura** intacta — é ela que os testes exercitam. Documente em `fixtures/README.md` que os arquivos foram sanitizados à mão.

- [ ] **Step 4: Criar o runner de testes**

```bash
#!/usr/bin/env bash
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR/.."
python3 -m unittest discover -s tests/unit -p 'test_*.py' -v
```

- [ ] **Step 5: Verificar que o runner roda sem testes**

Run: `mkdir -p plugins/cmux-hibernate/tests/unit && bash plugins/cmux-hibernate/tests/run-tests.sh`
Expected: `Ran 0 tests` e saída `OK`.

- [ ] **Step 6: Commit**

```bash
git add plugins/cmux-hibernate/.claude-plugin plugins/cmux-hibernate/tests plugins/cmux-hibernate/scripts/lib/__init__.py
git commit -m "feat(cmux-hibernate): cria esqueleto do plugin e fixtures de teste"
```

---

### Task 2: Parsing da árvore do cmux

**Files:**
- Create: `plugins/cmux-hibernate/scripts/lib/cmux_state.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_parse_tree.py`

**Interfaces:**
- Consumes: fixture `tests/fixtures/tree.txt` (Task 1).
- Produces:
  - `@dataclass Aba(uuid: str, ref: str, tipo: str, titulo: str, sessao: Optional[str]=None, cwd: Optional[str]=None, fonte: Optional[str]=None, transcript: Optional[dict]=None, estagnada: bool=False, url: Optional[str]=None)`
  - `@dataclass Pane(uuid: str, ref: str, abas: List[Aba])`
  - `@dataclass Workspace(uuid: str, ref: str, nome: str, panes: List[Pane])`
  - `@dataclass Janela(uuid: str, ref: str, workspaces: List[Workspace])`
  - `@dataclass Estado(janelas: List[Janela])` com método `todas_abas() -> Iterator[Tuple[Janela, Workspace, Pane, Aba]]`
  - `parse_tree(texto: str) -> List[Janela]`

- [ ] **Step 1: Escrever o teste que falha**

```python
import unittest, pathlib, sys
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import parse_tree, Estado

FIXTURE = (RAIZ / "tests/fixtures/tree.txt").read_text()

class TestParseTree(unittest.TestCase):
    def setUp(self):
        self.janelas = parse_tree(FIXTURE)
        self.estado = Estado(janelas=self.janelas)

    def test_encontra_janelas(self):
        self.assertGreater(len(self.janelas), 0)
        for j in self.janelas:
            self.assertRegex(j.uuid, r"^[0-9A-F-]{36}$")
            self.assertRegex(j.ref, r"^window:\d+$")

    def test_workspaces_tem_nome(self):
        nomes = [w.nome for j in self.janelas for w in j.workspaces]
        self.assertGreater(len(nomes), 0)
        self.assertTrue(all(isinstance(n, str) for n in nomes))

    def test_abas_carregam_tipo_e_uuid(self):
        abas = [a for *_, a in self.estado.todas_abas()]
        self.assertGreater(len(abas), 0)
        for a in abas:
            self.assertIn(a.tipo, {"terminal", "browser", "markdown"})
            self.assertRegex(a.uuid, r"^[0-9A-F-]{36}$")

    def test_hierarquia_preservada(self):
        # toda aba pertence a um pane, que pertence a um workspace, que pertence a uma janela
        for janela, ws, pane, aba in self.estado.todas_abas():
            self.assertIn(pane, ws.panes)
            self.assertIn(ws, janela.workspaces)

    def test_browser_captura_url(self):
        browsers = [a for *_, a in self.estado.todas_abas() if a.tipo == "browser"]
        for b in browsers:
            self.assertTrue(b.url is None or b.url.startswith("http"))

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_parse_tree -v` (a partir de `plugins/cmux-hibernate/`)
Expected: FAIL com `ModuleNotFoundError: No module named 'lib.cmux_state'`

- [ ] **Step 3: Implementar o parser**

```python
"""Deriva o estado real do cmux cruzando processo, filesystem e CLI."""
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Tuple
import re

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
                ref=m.group(1), uuid=m.group(2), tipo=m.group(3),
                titulo=m.group(4), url=url.group(1) if url else None,
            ))
    return janelas
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `bash tests/run-tests.sh`
Expected: 5 testes PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/cmux-hibernate/scripts/lib/cmux_state.py plugins/cmux-hibernate/tests/unit/test_parse_tree.py
git commit -m "feat(cmux-hibernate): faz parsing da arvore de janelas, workspaces e abas"
```

---

### Task 3: Vínculo sessão↔aba pelo processo (a correção central)

**Files:**
- Modify: `plugins/cmux-hibernate/scripts/lib/cmux_state.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_processos.py`

**Interfaces:**
- Consumes: `Aba`, `Estado` (Task 2).
- Produces:
  - `parse_processos(saida_ps: str) -> Dict[str, dict]` → `{surface_uuid: {"sessao": str, "pid": str}}`
  - `resolver_cwd(pid: str) -> Optional[str]` (usa `lsof`, isolado para poder ser mockado)
  - `aplicar_processos(estado: Estado, mapa: Dict[str, dict], cwds: Dict[str, str]) -> None` — preenche `sessao`, `cwd` e marca `fonte="processo"`

- [ ] **Step 1: Escrever o teste que falha, incluindo a regressão**

```python
import unittest, pathlib, sys
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import parse_tree, parse_processos, aplicar_processos, Estado

FIX_TREE = (RAIZ / "tests/fixtures/tree.txt").read_text()
FIX_PS = (RAIZ / "tests/fixtures/ps-eww.txt").read_text()

class TestProcessos(unittest.TestCase):
    def test_extrai_sessao_e_surface(self):
        mapa = parse_processos(FIX_PS)
        self.assertGreater(len(mapa), 0)
        for surface, info in mapa.items():
            self.assertRegex(surface, r"^[0-9A-F-]{36}$")
            self.assertRegex(info["sessao"], r"^[0-9a-f-]{36}$")

    def test_aplica_no_estado_e_marca_fonte(self):
        estado = Estado(janelas=parse_tree(FIX_TREE))
        mapa = parse_processos(FIX_PS)
        aplicar_processos(estado, mapa, cwds={})
        com_sessao = [a for *_, a in estado.todas_abas() if a.sessao]
        self.assertGreater(len(com_sessao), 0)
        self.assertTrue(all(a.fonte == "processo" for a in com_sessao))

    def test_regressao_binding_desatualizado(self):
        """Binding diz sessao A; processo roda sessao B. Deve vencer B.

        Foi esta falha que escondeu 7 conversas no ciclo de 27-28/07/2026.
        """
        estado = Estado(janelas=parse_tree(FIX_TREE))
        alvo = next(a for *_, a in estado.todas_abas() if a.tipo == "terminal")
        # simula binding velho ja preenchido
        alvo.sessao, alvo.fonte = "aaaaaaaa-1111-2222-3333-444444444444", "binding"
        mapa = {alvo.uuid: {"sessao": "bbbbbbbb-5555-6666-7777-888888888888", "pid": "999"}}
        aplicar_processos(estado, mapa, cwds={"999": "/tmp/projeto"})
        self.assertEqual(alvo.sessao, "bbbbbbbb-5555-6666-7777-888888888888")
        self.assertEqual(alvo.fonte, "processo")
        self.assertEqual(alvo.cwd, "/tmp/projeto")

    def test_ignora_daemon_e_bg(self):
        linhas = [
            "111 /Users/x/.local/bin/claude daemon run --json-path /x CMUX_SURFACE_ID=AAAAAAAA-1111-2222-3333-444444444444",
            "222 /Users/x/.local/bin/claude --resume bbbbbbbb-5555-6666-7777-888888888888 CMUX_SURFACE_ID=CCCCCCCC-1111-2222-3333-444444444444",
        ]
        mapa = parse_processos("\n".join(linhas))
        self.assertEqual(len(mapa), 1)
        self.assertIn("CCCCCCCC-1111-2222-3333-444444444444", mapa)

    def test_detecta_sessao_duplicada(self):
        """Mesma sessao em duas abas e' anomalia: nao desarmar nem subir."""
        from lib.cmux_state import detectar_duplicatas
        linhas = [
            "1 /Users/x/.local/bin/claude --resume dddddddd-1111-2222-3333-444444444444 CMUX_SURFACE_ID=AAAAAAAA-1111-2222-3333-444444444444",
            "2 /Users/x/.local/bin/claude --resume dddddddd-1111-2222-3333-444444444444 CMUX_SURFACE_ID=BBBBBBBB-1111-2222-3333-444444444444",
        ]
        mapa = parse_processos("\n".join(linhas))
        self.assertEqual(detectar_duplicatas(mapa), ["dddddddd-1111-2222-3333-444444444444"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_processos -v`
Expected: FAIL com `ImportError: cannot import name 'parse_processos'`

- [ ] **Step 3: Implementar**

Acrescentar a `lib/cmux_state.py`:

```python
import subprocess
from typing import Dict

_RE_SESSAO = re.compile(r"--(?:resume|session-id)\s+([0-9a-f-]{36})")
_RE_SURFACE = re.compile(r"CMUX_SURFACE_ID=([0-9A-F-]{36})")

def parse_processos(saida_ps: str) -> Dict[str, dict]:
    """Mapeia surface_uuid -> {sessao, pid} a partir de 'ps eww' com env anexado.

    Ignora processos auxiliares (daemon, bg-pty-host, bg-spare): eles carregam
    CMUX_SURFACE_ID herdado e roubariam a aba da sessao real.
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
    try:
        saida = subprocess.run(["lsof", "-a", "-p", pid, "-d", "cwd", "-Fn"],
                               capture_output=True, text=True, timeout=10).stdout
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
    """Sessoes que aparecem em mais de uma aba — estado anomalo.

    Nao desarmar nem subir essas: escrever binding em duas abas para a mesma
    sessao produziria duas instancias competindo pelo mesmo transcript.
    """
    contagem: Dict[str, int] = {}
    for info in mapa.values():
        contagem[info["sessao"]] = contagem.get(info["sessao"], 0) + 1
    return sorted(s for s, n in contagem.items() if n > 1)
```

Adicionar `import os` ao topo do módulo.

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `bash tests/run-tests.sh`
Expected: 10 testes PASS (5 da Task 2 + 5 desta).

- [ ] **Step 5: Commit**

```bash
git add plugins/cmux-hibernate/scripts/lib/cmux_state.py plugins/cmux-hibernate/tests/unit/test_processos.py
git commit -m "feat(cmux-hibernate): vincula sessao e aba pelo processo, com teste de regressao"
```

---

### Task 4: Transcripts, estagnação e slug divergente

**Files:**
- Modify: `plugins/cmux-hibernate/scripts/lib/cmux_state.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_transcripts.py`

**Interfaces:**
- Consumes: `Aba` (Task 2).
- Produces:
  - `localizar_transcript(sessao: str, raiz: Path) -> Optional[Path]` — varre `raiz/*/{sessao}.jsonl`
  - `cwd_do_transcript(caminho: Path) -> Optional[str]` — lê o campo `cwd` das primeiras 40 linhas
  - `marcar_estagnadas(estado: Estado, agora: float, stale_days: int = 7) -> None`
  - Constante `STALE_DAYS = 7`

- [ ] **Step 1: Escrever o teste que falha**

```python
import unittest, tempfile, json, pathlib, sys, time, os
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import (localizar_transcript, cwd_do_transcript,
                            marcar_estagnadas, Estado, Janela, Workspace, Pane, Aba)

class TestTranscripts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = pathlib.Path(self.tmp.name)
        # dois slugs diferentes para o mesmo projeto — o cenario do symlink
        (self.raiz / "-Users-x-Documents-tech-projects-app").mkdir(parents=True)
        (self.raiz / "-Users-x-tech-projects-app").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _escrever(self, slug, sessao, cwd):
        p = self.raiz / slug / (sessao + ".jsonl")
        p.write_text(json.dumps({"cwd": cwd, "message": {"role": "user"}}) + "\n")
        return p

    def test_localiza_em_qualquer_slug(self):
        sessao = "11111111-2222-3333-4444-555555555555"
        self._escrever("-Users-x-Documents-tech-projects-app", sessao, "/Users/x/tech_projects/app")
        achado = localizar_transcript(sessao, self.raiz)
        self.assertIsNotNone(achado)
        self.assertTrue(achado.name.startswith(sessao))

    def test_cwd_vem_de_dentro_do_arquivo_nao_do_slug(self):
        """O nome do diretorio pode mentir apos um symlink; o conteudo, nao."""
        sessao = "66666666-7777-8888-9999-000000000000"
        p = self._escrever("-Users-x-Documents-tech-projects-app", sessao, "/Users/x/tech_projects/app")
        self.assertEqual(cwd_do_transcript(p), "/Users/x/tech_projects/app")

    def test_transcript_ausente_retorna_none(self):
        self.assertIsNone(localizar_transcript("00000000-0000-0000-0000-000000000000", self.raiz))

    def test_marca_estagnada_por_mtime(self):
        agora = time.time()
        aba_velha = Aba(uuid="A"*8, ref="surface:1", tipo="terminal", titulo="velha",
                        sessao="s1", transcript={"mtime": agora - 10 * 86400})
        aba_nova = Aba(uuid="B"*8, ref="surface:2", tipo="terminal", titulo="nova",
                       sessao="s2", transcript={"mtime": agora - 3600})
        estado = Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
            Workspace(uuid="S", ref="workspace:1", nome="ws",
                      panes=[Pane(uuid="P", ref="pane:1", abas=[aba_velha, aba_nova])])])])
        marcar_estagnadas(estado, agora=agora, stale_days=7)
        self.assertTrue(aba_velha.estagnada)
        self.assertFalse(aba_nova.estagnada)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_transcripts -v`
Expected: FAIL com `ImportError: cannot import name 'localizar_transcript'`

- [ ] **Step 3: Implementar**

```python
import json
from pathlib import Path

STALE_DAYS = 7
RAIZ_PROJETOS = Path.home() / ".claude" / "projects"

def localizar_transcript(sessao: str, raiz: Path = RAIZ_PROJETOS) -> Optional[Path]:
    """Acha o .jsonl da sessao em qualquer slug de projeto.

    O slug do diretorio deriva do caminho e pode divergir apos um symlink;
    por isso a busca e' por session id, nao por projeto.
    """
    achados = sorted(raiz.glob("*/" + sessao + ".jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    return achados[0] if achados else None

def cwd_do_transcript(caminho: Path) -> Optional[str]:
    """Le o cwd gravado dentro do transcript — a unica fonte que nao mente."""
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

def marcar_estagnadas(estado: Estado, agora: float, stale_days: int = STALE_DAYS) -> None:
    limite = agora - stale_days * 86400
    for *_, aba in estado.todas_abas():
        if aba.transcript and aba.transcript.get("mtime", 0) < limite:
            aba.estagnada = True
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `bash tests/run-tests.sh`
Expected: 14 testes PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/cmux-hibernate/scripts/lib/cmux_state.py plugins/cmux-hibernate/tests/unit/test_transcripts.py
git commit -m "feat(cmux-hibernate): localiza transcripts por sessao e marca estagnadas"
```

---

### Task 5: Leitura integrada do estado

**Files:**
- Modify: `plugins/cmux-hibernate/scripts/lib/cmux_state.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_ler_estado.py`

**Interfaces:**
- Consumes: tudo das Tasks 2–4.
- Produces:
  - `cmux_bin() -> str`
  - `rodar_cmux(*args: str) -> str`
  - `ler_estado(raiz_projetos: Path = RAIZ_PROJETOS) -> Estado` — orquestra tree → processos → transcripts → estagnação
  - `binding_de(janela_uuid, ws_uuid, surface_uuid) -> Optional[dict]` — complemento, `fonte="binding"`

- [ ] **Step 1: Escrever o teste que falha**

```python
import unittest, pathlib, sys
from unittest import mock
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib import cmux_state

FIX_TREE = (RAIZ / "tests/fixtures/tree.txt").read_text()
FIX_PS = (RAIZ / "tests/fixtures/ps-eww.txt").read_text()

class TestLerEstado(unittest.TestCase):
    def test_orquestra_sem_tocar_no_sistema(self):
        with mock.patch.object(cmux_state, "rodar_cmux", return_value=FIX_TREE), \
             mock.patch.object(cmux_state, "_ps_eww", return_value=FIX_PS), \
             mock.patch.object(cmux_state, "resolver_cwd", return_value="/tmp/x"), \
             mock.patch.object(cmux_state, "localizar_transcript", return_value=None):
            estado = cmux_state.ler_estado()
        abas = [a for *_, a in estado.todas_abas()]
        self.assertGreater(len(abas), 0)
        com_sessao = [a for a in abas if a.sessao]
        self.assertTrue(all(a.fonte == "processo" for a in com_sessao))

    def test_cmux_bin_respeita_env(self):
        with mock.patch.dict("os.environ", {"CMUX_BUNDLED_CLI_PATH": "/custom/cmux"}):
            self.assertEqual(cmux_state.cmux_bin(), "/custom/cmux")

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_ler_estado -v`
Expected: FAIL — `ler_estado` não existe.

- [ ] **Step 3: Implementar**

```python
import shutil, time

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
    r = subprocess.run([cmux_bin(), *args], capture_output=True, text=True, env=env, timeout=30)
    return r.stdout

def _ps_eww() -> str:
    """Uma linha por processo claude, com o environment anexado."""
    base = subprocess.run(["ps", "-A", "-ww", "-o", "pid=,command="],
                          capture_output=True, text=True).stdout
    linhas = []
    for l in base.splitlines():
        if "/.local/bin/claude" not in l or " daemon run" in l:
            continue
        pid = l.split()[0]
        env = subprocess.run(["ps", "eww", "-o", "command=", "-p", pid],
                             capture_output=True, text=True).stdout.replace("\n", " ")
        linhas.append(pid + " " + env)
    return "\n".join(linhas)

def ler_estado(raiz_projetos: Path = RAIZ_PROJETOS) -> Estado:
    estado = Estado(janelas=parse_tree(rodar_cmux("tree", "--all", "--id-format", "both")))
    mapa = parse_processos(_ps_eww())
    cwds = {}
    for info in mapa.values():
        cwd = resolver_cwd(info["pid"])
        if cwd:
            cwds[info["pid"]] = cwd
    aplicar_processos(estado, mapa, cwds)

    for *_, aba in estado.todas_abas():
        if not aba.sessao:
            continue
        caminho = localizar_transcript(aba.sessao, raiz_projetos)
        if caminho:
            st = caminho.stat()
            aba.transcript = {"path": str(caminho), "kb": st.st_size // 1024, "mtime": st.st_mtime}
            if not aba.cwd:
                aba.cwd = cwd_do_transcript(caminho)
    marcar_estagnadas(estado, agora=time.time())
    return estado
```

- [ ] **Step 4: Rodar e confirmar que passa**

Run: `bash tests/run-tests.sh`
Expected: 16 testes PASS.

- [ ] **Step 5: Commit**

```bash
git add plugins/cmux-hibernate/scripts/lib/cmux_state.py plugins/cmux-hibernate/tests/unit/test_ler_estado.py
git commit -m "feat(cmux-hibernate): integra leitura de estado a partir de todas as fontes"
```

---

### Task 6: `hibernate.py` — snapshot e relatório (sem mutar)

**Files:**
- Create: `plugins/cmux-hibernate/scripts/hibernate.py`
- Create: `plugins/cmux-hibernate/scripts/lib/snapshot.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_snapshot.py`

**Interfaces:**
- Consumes: `Estado`, `ler_estado` (Task 5).
- Produces:
  - `serializar(estado: Estado, aba_controle: Optional[str], stale_days: int) -> dict`
  - `gravar(dados: dict, base: Path) -> Path` — cria `<base>/<ISO>/snapshot.json` + `INVENTARIO.md`
  - `aplicar_retencao(base: Path, manter: int = 5) -> List[Path]` — devolve os removidos
  - `BASE_ESTADO = Path.home()/".local/state/cmux-hibernate"`

- [ ] **Step 1: Escrever o teste que falha**

```python
import unittest, tempfile, pathlib, sys, json
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Estado, Janela, Workspace, Pane, Aba
from lib.snapshot import serializar, gravar, aplicar_retencao

def estado_exemplo():
    aba = Aba(uuid="U1", ref="surface:1", tipo="terminal", titulo="tarefa",
              sessao="11111111-2222-3333-4444-555555555555", cwd="/tmp/p",
              fonte="processo", transcript={"path": "/t.jsonl", "kb": 10, "mtime": 1.0})
    return Estado(janelas=[Janela(uuid="W1", ref="window:1", workspaces=[
        Workspace(uuid="S1", ref="workspace:1", nome="proj",
                  panes=[Pane(uuid="P1", ref="pane:1", abas=[aba])])])])

class TestSnapshot(unittest.TestCase):
    def test_serializa_hierarquia_e_metadados(self):
        d = serializar(estado_exemplo(), aba_controle="U1", stale_days=7)
        self.assertEqual(d["aba_de_controle"], "U1")
        self.assertEqual(d["stale_days"], 7)
        aba = d["janelas"][0]["workspaces"][0]["panes"][0]["abas"][0]
        self.assertEqual(aba["sessao"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(aba["fonte"], "processo")

    def test_nao_grava_campo_volatil(self):
        """Nada que afirme estado do momento — envelheceria em silencio."""
        d = serializar(estado_exemplo(), aba_controle=None, stale_days=7)
        aba = d["janelas"][0]["workspaces"][0]["panes"][0]["abas"][0]
        for proibido in ("rodando", "viva", "alive", "pid"):
            self.assertNotIn(proibido, aba)

    def test_grava_snapshot_e_inventario(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = gravar(serializar(estado_exemplo(), "U1", 7), pathlib.Path(tmp))
            self.assertTrue((destino / "snapshot.json").exists())
            self.assertTrue((destino / "INVENTARIO.md").exists())
            lido = json.loads((destino / "snapshot.json").read_text())
            self.assertEqual(lido["aba_de_controle"], "U1")

    def test_retencao_mantem_os_cinco_mais_recentes(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            for i in range(8):
                d = base / ("2026-08-04T10-0%d" % i)
                d.mkdir()
                (d / "snapshot.json").write_text("{}")
            removidos = aplicar_retencao(base, manter=5)
            self.assertEqual(len(removidos), 3)
            self.assertEqual(len(list(base.iterdir())), 5)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_snapshot -v`
Expected: FAIL — `lib.snapshot` não existe.

- [ ] **Step 3: Implementar `lib/snapshot.py`**

```python
"""Serializacao e persistencia do snapshot de hibernacao."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json, shutil

BASE_ESTADO = Path.home() / ".local" / "state" / "cmux-hibernate"

def serializar(estado, aba_controle: Optional[str], stale_days: int) -> dict:
    return {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "metodo": "CMUX_SURFACE_ID (processo)",
        "stale_days": stale_days,
        "aba_de_controle": aba_controle,
        "janelas": [{
            "uuid": j.uuid, "ref": j.ref,
            "workspaces": [{
                "uuid": w.uuid, "ref": w.ref, "nome": w.nome,
                "panes": [{
                    "uuid": p.uuid, "ref": p.ref,
                    "abas": [_aba(a) for a in p.abas],
                } for p in w.panes],
            } for w in j.workspaces],
        } for j in estado.janelas],
    }

def _aba(a) -> dict:
    d = {"uuid": a.uuid, "ref": a.ref, "tipo": a.tipo, "titulo": a.titulo,
         "sessao": a.sessao, "cwd": a.cwd, "fonte": a.fonte,
         "transcript": a.transcript, "estagnada": a.estagnada}
    if a.url:
        d["url"] = a.url
    return d

def gravar(dados: dict, base: Path = BASE_ESTADO) -> Path:
    destino = base / datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "snapshot.json").write_text(json.dumps(dados, indent=2, ensure_ascii=False))
    (destino / "INVENTARIO.md").write_text(_inventario(dados))
    return destino

def _inventario(d: dict) -> str:
    linhas = ["# Snapshot cmux-hibernate", "",
              "**Gerado:** " + d["gerado_em"], "",
              "Retomada manual, se precisar reconstruir sem agente:", ""]
    for j in d["janelas"]:
        for w in j["workspaces"]:
            abas = [a for p in w["panes"] for a in p["abas"] if a.get("sessao")]
            if not abas:
                continue
            linhas.append("## " + w["nome"])
            linhas.append("")
            for a in abas:
                marca = " *(estagnada)*" if a.get("estagnada") else ""
                linhas.append("- " + (a["titulo"] or "sem titulo")[:70] + marca)
                linhas.append("  ```")
                linhas.append("  cd '%s' && claude --resume %s --dangerously-skip-permissions"
                              % (a.get("cwd") or "~", a["sessao"]))
                linhas.append("  ```")
            linhas.append("")
    return "\n".join(linhas)

def aplicar_retencao(base: Path, manter: int = 5) -> List[Path]:
    if not base.exists():
        return []
    dirs = sorted([d for d in base.iterdir() if d.is_dir()], reverse=True)
    removidos = dirs[manter:]
    for d in removidos:
        shutil.rmtree(d)
    return removidos
```

- [ ] **Step 4: Implementar `hibernate.py` (somente leitura nesta task)**

```python
#!/usr/bin/env python3
"""Hiberna as sessoes Claude Code do cmux: retrata, desarma e libera memoria."""
import argparse, os, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.cmux_state import (ler_estado, STALE_DAYS, detectar_duplicatas,
                            parse_processos, _ps_eww)
from lib.snapshot import serializar, gravar, aplicar_retencao, BASE_ESTADO

def main() -> int:
    ap = argparse.ArgumentParser(description="Hiberna sessoes Claude Code no cmux.")
    ap.add_argument("--apply", action="store_true",
                    help="desarma os bindings de fato (padrao: apenas retrata)")
    ap.add_argument("--all", action="store_true",
                    help="desarma tambem a aba de onde o comando foi chamado")
    ap.add_argument("--stale-days", type=int, default=STALE_DAYS)
    args = ap.parse_args()

    estado = ler_estado()
    controle = None if args.all else os.environ.get("CMUX_SURFACE_ID")

    abas = [a for *_, a in estado.todas_abas() if a.sessao]
    estagnadas = [a for a in abas if a.estagnada]

    print("Estado real: %d sessoes em %d workspaces, %d janelas" % (
        len(abas),
        sum(len(j.workspaces) for j in estado.janelas),
        len(estado.janelas)))
    if estagnadas:
        print("\n  %d sem atividade ha mais de %d dias:" % (len(estagnadas), args.stale_days))
        for a in estagnadas:
            print("      %s  %s" % (a.sessao[:8], a.titulo[:58]))

    dados = serializar(estado, controle, args.stale_days)
    destino = gravar(dados, BASE_ESTADO)
    aplicar_retencao(BASE_ESTADO)
    print("\n  Snapshot: %s" % destino)
    if not args.apply:
        print("  (dry-run — nada foi desarmado; use --apply)")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Rodar os testes e o comando em dry-run**

Run:
```bash
bash tests/run-tests.sh
python3 scripts/hibernate.py
```
Expected: 20 testes PASS; o comando imprime o total real de sessões e grava um snapshot, sem mutar nada.

- [ ] **Step 6: Commit**

```bash
git add plugins/cmux-hibernate/scripts/hibernate.py plugins/cmux-hibernate/scripts/lib/snapshot.py plugins/cmux-hibernate/tests/unit/test_snapshot.py
git commit -m "feat(cmux-hibernate): grava snapshot e inventario em modo dry-run"
```

---

### Task 7: `hibernate.py` — desarme dos bindings

**Files:**
- Modify: `plugins/cmux-hibernate/scripts/hibernate.py`
- Create: `plugins/cmux-hibernate/scripts/lib/bindings.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_bindings.py`

**Interfaces:**
- Consumes: `Estado` (Task 2), `rodar_cmux` (Task 5).
- Produces:
  - `comando_resume(sessao: str) -> List[str]` → `["claude", "--resume", sessao, "--dangerously-skip-permissions"]`
  - `desarmar(janela_uuid, ws_uuid, surface_uuid, sessao, cwd) -> bool`
  - `planejar_desarme(estado, aba_controle) -> List[dict]` — puro, testável sem cmux

- [ ] **Step 1: Escrever o teste que falha**

```python
import unittest, pathlib, sys
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Estado, Janela, Workspace, Pane, Aba
from lib.bindings import comando_resume, planejar_desarme

def estado(com_controle=True):
    a1 = Aba(uuid="CTRL", ref="surface:1", tipo="terminal", titulo="controle",
             sessao="11111111-1111-1111-1111-111111111111", cwd="/tmp/a", fonte="processo")
    a2 = Aba(uuid="OUTRA", ref="surface:2", tipo="terminal", titulo="outra",
             sessao="22222222-2222-2222-2222-222222222222", cwd="/tmp/b", fonte="processo")
    a3 = Aba(uuid="SHELL", ref="surface:3", tipo="terminal", titulo="shell")
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="ws",
                  panes=[Pane(uuid="P", ref="pane:1", abas=[a1, a2, a3])])])])

class TestBindings(unittest.TestCase):
    def test_comando_resume(self):
        self.assertEqual(comando_resume("abc"),
                         ["claude", "--resume", "abc", "--dangerously-skip-permissions"])

    def test_preserva_aba_de_controle(self):
        plano = planejar_desarme(estado(), aba_controle="CTRL")
        alvos = [p["surface"] for p in plano]
        self.assertIn("OUTRA", alvos)
        self.assertNotIn("CTRL", alvos)

    def test_ignora_aba_sem_sessao(self):
        plano = planejar_desarme(estado(), aba_controle=None)
        self.assertNotIn("SHELL", [p["surface"] for p in plano])

    def test_sem_controle_desarma_todas(self):
        plano = planejar_desarme(estado(), aba_controle=None)
        self.assertEqual(len(plano), 2)

    def test_plano_carrega_cwd_e_sessao(self):
        plano = planejar_desarme(estado(), aba_controle="CTRL")
        self.assertEqual(plano[0]["cwd"], "/tmp/b")
        self.assertEqual(plano[0]["sessao"], "22222222-2222-2222-2222-222222222222")

    def test_pula_sessoes_duplicadas(self):
        """Caso de borda do spec §7: sessao em duas abas nao e' desarmada."""
        plano = planejar_desarme(estado(), aba_controle=None,
                                 duplicadas=["22222222-2222-2222-2222-222222222222"])
        self.assertEqual([p["sessao"] for p in plano],
                         ["11111111-1111-1111-1111-111111111111"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_bindings -v`
Expected: FAIL — `lib.bindings` não existe.

- [ ] **Step 3: Implementar `lib/bindings.py`**

```python
"""Escrita de resumeBinding no cmux.

Nota de arquitetura: o CLI grava sempre auto_resume=false. Nao existe
"rearmar" — desarmar e' via de mao unica. Por isso a aba de controle precisa
ser escolhida no momento do hibernate.
"""
from typing import List, Optional
from lib.cmux_state import rodar_cmux

def comando_resume(sessao: str) -> List[str]:
    return ["claude", "--resume", sessao, "--dangerously-skip-permissions"]

def planejar_desarme(estado, aba_controle: Optional[str],
                     duplicadas: Optional[List[str]] = None) -> List[dict]:
    """Monta o plano de desarme. Pula a aba de controle e sessoes duplicadas."""
    proibidas = set(duplicadas or [])
    plano = []
    for janela, ws, _pane, aba in estado.todas_abas():
        if not aba.sessao or aba.uuid == aba_controle or aba.sessao in proibidas:
            continue
        plano.append({"janela": janela.uuid, "workspace": ws.uuid, "surface": aba.uuid,
                      "sessao": aba.sessao, "cwd": aba.cwd, "titulo": aba.titulo})
    return plano

def desarmar(janela: str, workspace: str, surface: str, sessao: str, cwd: str) -> bool:
    saida = rodar_cmux(
        "surface", "resume", "set",
        "--window", janela, "--workspace", workspace, "--surface", surface,
        "--cwd", cwd, "--name", "Claude Code", "--kind", "claude",
        "--checkpoint", sessao, "--source", "agent-hook",
        "--", *comando_resume(sessao))
    return "OK" in saida
```

- [ ] **Step 4: Ligar ao `hibernate.py`**

Substituir o bloco final de `main()` (a partir de `dados = serializar(...)`) por:

```python
    dados = serializar(estado, controle, args.stale_days)
    destino = gravar(dados, BASE_ESTADO)
    aplicar_retencao(BASE_ESTADO)

    duplicadas = detectar_duplicatas(parse_processos(_ps_eww()))
    if duplicadas:
        print("\n  anomalia: %d sessoes aparecem em mais de uma aba; serao puladas" % len(duplicadas))
    plano = planejar_desarme(estado, controle, duplicadas)
    if not args.apply:
        print("\n  Desarmaria %d abas (dry-run). Use --apply para valer." % len(plano))
    else:
        ok = 0
        for p in plano:
            if p["cwd"] and desarmar(p["janela"], p["workspace"], p["surface"],
                                     p["sessao"], p["cwd"]):
                ok += 1
            else:
                print("      falhou: %s  %s" % (p["sessao"][:8], p["titulo"][:50]))
        print("\n  Desarmadas: %d abas   (sobem so quando voce abrir)" % ok)
        print("  Preservada: %s" % ("nenhuma (--all)" if controle is None else "1 (esta aba)"))
    print("\n  Snapshot: %s" % destino)
    if args.apply:
        print("  Pode dar Cmd+Q.")
    return 0
```

Acrescentar ao topo: `from lib.bindings import planejar_desarme, desarmar`

- [ ] **Step 5: Rodar testes e um dry-run**

Run:
```bash
bash tests/run-tests.sh
python3 scripts/hibernate.py
```
Expected: 26 testes PASS; dry-run informa quantas abas desarmaria, sem mutar.

- [ ] **Step 6: Commit**

```bash
git add plugins/cmux-hibernate/scripts/lib/bindings.py plugins/cmux-hibernate/scripts/hibernate.py plugins/cmux-hibernate/tests/unit/test_bindings.py
git commit -m "feat(cmux-hibernate): desarma bindings preservando a aba de controle"
```

---

### Task 8: `wake.py` — diferença e relatório

**Files:**
- Create: `plugins/cmux-hibernate/scripts/wake.py`
- Create: `plugins/cmux-hibernate/scripts/lib/diff.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_diff.py`

**Interfaces:**
- Consumes: `Estado` (Task 2), snapshot serializado (Task 6).
- Produces:
  - `carregar_snapshot(base: Path, escolhido: Optional[Path]) -> Tuple[dict, Path]`
  - `idade_em_dias(dados: dict, agora: float) -> float`
  - `comparar(dados: dict, estado) -> dict` → `{"vivas": [...], "dormindo": [...], "ausentes": [...], "sem_transcript": [...]}`
  - `MAX_SNAPSHOT_AGE = 3`

- [ ] **Step 1: Escrever o teste que falha**

```python
import unittest, pathlib, sys, time
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Estado, Janela, Workspace, Pane, Aba
from lib.diff import comparar, idade_em_dias

SNAP = {
    "gerado_em": "2026-08-04T14:22:31",
    "janelas": [{"uuid": "W", "ref": "window:1", "workspaces": [{
        "uuid": "S", "ref": "workspace:1", "nome": "proj", "panes": [{
            "uuid": "P", "ref": "pane:1", "abas": [
                {"uuid": "A1", "sessao": "1111", "titulo": "viva", "cwd": "/tmp/a",
                 "tipo": "terminal", "transcript": {"path": "/t1.jsonl"}},
                {"uuid": "A2", "sessao": "2222", "titulo": "dormindo", "cwd": "/tmp/b",
                 "tipo": "terminal", "transcript": {"path": "/t2.jsonl"}},
                {"uuid": "A3", "sessao": "3333", "titulo": "sumiu", "cwd": "/tmp/c",
                 "tipo": "terminal", "transcript": {"path": "/t3.jsonl"}},
            ]}]}]}]}

def estado_atual():
    viva = Aba(uuid="A1", ref="surface:1", tipo="terminal", titulo="viva",
               sessao="1111", fonte="processo")
    dormindo = Aba(uuid="A2", ref="surface:2", tipo="terminal", titulo="dormindo")
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="proj",
                  panes=[Pane(uuid="P", ref="pane:1", abas=[viva, dormindo])])])])

class TestDiff(unittest.TestCase):
    def setUp(self):
        self.r = comparar(SNAP, estado_atual())

    def test_identifica_viva(self):
        self.assertEqual([x["sessao"] for x in self.r["vivas"]], ["1111"])

    def test_identifica_dormindo(self):
        """Aba existe na estrutura mas nenhum processo roda a sessao."""
        self.assertEqual([x["sessao"] for x in self.r["dormindo"]], ["2222"])

    def test_identifica_ausente(self):
        """Aba do snapshot que nao existe mais na estrutura atual."""
        self.assertEqual([x["sessao"] for x in self.r["ausentes"]], ["3333"])

    def test_chave_e_sessao_nao_titulo(self):
        """Titulos mentem: uma aba pode exibir o nome de outro projeto."""
        snap = {"janelas": [{"uuid": "W", "ref": "w", "workspaces": [{
            "uuid": "S", "ref": "s", "nome": "n", "panes": [{"uuid": "P", "ref": "p", "abas": [
                {"uuid": "A1", "sessao": "1111", "titulo": "TITULO COMPLETAMENTE DIFERENTE",
                 "cwd": "/tmp/a", "tipo": "terminal", "transcript": {"path": "/t.jsonl"}}]}]}]}]}
        r = comparar(snap, estado_atual())
        self.assertEqual(len(r["vivas"]), 1)

    def test_idade_em_dias(self):
        base = time.mktime(time.strptime("2026-08-04T14:22:31", "%Y-%m-%dT%H:%M:%S"))
        self.assertAlmostEqual(idade_em_dias(SNAP, base + 2 * 86400), 2.0, places=1)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_diff -v`
Expected: FAIL — `lib.diff` não existe.

- [ ] **Step 3: Implementar `lib/diff.py`**

```python
"""Compara o snapshot com o estado real. Chave sempre por session id."""
from pathlib import Path
from typing import Optional, Tuple
import json, time

MAX_SNAPSHOT_AGE = 3

def carregar_snapshot(base: Path, escolhido: Optional[Path] = None) -> Tuple[dict, Path]:
    if escolhido:
        return json.loads((escolhido / "snapshot.json").read_text()), escolhido
    if not base.exists():
        raise RuntimeError("nenhum snapshot em %s — rode o hibernate antes" % base)
    dirs = sorted([d for d in base.iterdir() if (d / "snapshot.json").exists()], reverse=True)
    if not dirs:
        raise RuntimeError("nenhum snapshot em %s — rode o hibernate antes" % base)
    return json.loads((dirs[0] / "snapshot.json").read_text()), dirs[0]

def idade_em_dias(dados: dict, agora: float) -> float:
    t = time.mktime(time.strptime(dados["gerado_em"], "%Y-%m-%dT%H:%M:%S"))
    return (agora - t) / 86400.0

def _abas_do_snapshot(dados: dict):
    for j in dados["janelas"]:
        for w in j["workspaces"]:
            for p in w["panes"]:
                for a in p["abas"]:
                    if a.get("sessao"):
                        yield j, w, a

def comparar(dados: dict, estado) -> dict:
    vivas_agora = {a.sessao for *_, a in estado.todas_abas() if a.sessao and a.fonte == "processo"}
    uuids_atuais = {a.uuid for *_, a in estado.todas_abas()}
    r = {"vivas": [], "dormindo": [], "ausentes": [], "sem_transcript": []}
    for j, w, a in _abas_do_snapshot(dados):
        item = {"sessao": a["sessao"], "titulo": a.get("titulo", ""), "cwd": a.get("cwd"),
                "workspace": w["nome"], "janela": j["uuid"], "ws_uuid": w["uuid"],
                "surface": a["uuid"]}
        if not a.get("transcript"):
            r["sem_transcript"].append(item)
        elif a["sessao"] in vivas_agora:
            r["vivas"].append(item)
        elif a["uuid"] in uuids_atuais:
            r["dormindo"].append(item)
        else:
            r["ausentes"].append(item)
    return r
```

- [ ] **Step 4: Implementar `wake.py` (modo relatório)**

```python
#!/usr/bin/env python3
"""Confere e restaura o ambiente cmux a partir de um snapshot de hibernacao."""
import argparse, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.cmux_state import ler_estado
from lib.snapshot import BASE_ESTADO
from lib.diff import carregar_snapshot, comparar, idade_em_dias, MAX_SNAPSHOT_AGE

def main() -> int:
    ap = argparse.ArgumentParser(description="Restaura sessoes Claude Code no cmux.")
    ap.add_argument("--snapshot", type=Path, help="diretorio de um snapshot especifico")
    ap.add_argument("--max-age", type=float, default=MAX_SNAPSHOT_AGE)
    args = ap.parse_args()

    dados, origem = carregar_snapshot(BASE_ESTADO, args.snapshot)
    idade = idade_em_dias(dados, time.time())
    print("Snapshot de %s (%.1f dias) · %s" % (dados["gerado_em"], idade, origem.name))
    if idade > args.max_age:
        resp = input("  Snapshot com mais de %.0f dias. Continuar? [s/N] " % args.max_age)
        if resp.strip().lower() not in ("s", "sim", "y"):
            return 1

    r = comparar(dados, ler_estado())
    print("\n  rodando        %d" % len(r["vivas"]))
    print("  dormindo       %d  (sobem ao abrir a aba)" % len(r["dormindo"]))
    if r["ausentes"]:
        print("  ausentes       %d  (aba nao existe mais)" % len(r["ausentes"]))
        for x in r["ausentes"]:
            print("      %s  %s  ·  %s" % (x["sessao"][:8], x["workspace"], x["titulo"][:44]))
    if r["sem_transcript"]:
        print("  sem transcript %d  (nao restauraveis)" % len(r["sem_transcript"]))
    if not r["ausentes"]:
        print("\n  Nada a corrigir.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: Rodar testes e o relatório**

Run:
```bash
bash tests/run-tests.sh
python3 scripts/wake.py
```
Expected: 31 testes PASS; o relatório lista as sessões do snapshot mais recente.

- [ ] **Step 6: Commit**

```bash
git add plugins/cmux-hibernate/scripts/wake.py plugins/cmux-hibernate/scripts/lib/diff.py plugins/cmux-hibernate/tests/unit/test_diff.py
git commit -m "feat(cmux-hibernate): compara snapshot com estado real e relata divergencias"
```

---

### Task 9: `wake.py` — `--up` e `--rebuild`

**Files:**
- Modify: `plugins/cmux-hibernate/scripts/wake.py`
- Create: `plugins/cmux-hibernate/scripts/lib/restore.py`
- Test: `plugins/cmux-hibernate/tests/unit/test_restore.py`

**Interfaces:**
- Consumes: resultado de `comparar` (Task 8), `rodar_cmux` (Task 5), `comando_resume` (Task 7).
- Produces:
  - `filtrar_alvo(itens: List[dict], alvo: str) -> List[dict]` — `"all"` ou nome de workspace
  - `subir(item: dict) -> bool` — envia o comando via `cmux rpc surface.send_text`
  - `layout_do_workspace(ws: dict) -> dict` — JSON de `--layout`
  - `planejar_rebuild(dados: dict, estado) -> List[dict]` — só workspaces ausentes

- [ ] **Step 1: Escrever o teste que falha**

```python
import unittest, pathlib, sys, json
RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import Estado, Janela, Workspace, Pane, Aba
from lib.restore import filtrar_alvo, layout_do_workspace, planejar_rebuild

ITENS = [
    {"sessao": "1111", "workspace": "projeto-alfa", "titulo": "a", "cwd": "/tmp/a"},
    {"sessao": "2222", "workspace": "projeto-beta", "titulo": "b", "cwd": "/tmp/b"},
]

WS_SNAP = {"uuid": "S", "ref": "workspace:1", "nome": "proj", "panes": [
    {"uuid": "P1", "ref": "pane:1", "abas": [
        {"uuid": "A1", "tipo": "terminal", "sessao": "1111", "cwd": "/tmp/a", "titulo": "t1"},
        {"uuid": "A2", "tipo": "terminal", "sessao": None, "cwd": None, "titulo": "shell"}]},
    {"uuid": "P2", "ref": "pane:2", "abas": [
        {"uuid": "A3", "tipo": "browser", "url": "https://exemplo.com", "titulo": "web"}]}]}

class TestRestore(unittest.TestCase):
    def test_filtra_all(self):
        self.assertEqual(len(filtrar_alvo(ITENS, "all")), 2)

    def test_filtra_por_workspace(self):
        r = filtrar_alvo(ITENS, "projeto-alfa")
        self.assertEqual([x["sessao"] for x in r], ["1111"])

    def test_layout_um_pane(self):
        ws = {"uuid": "S", "nome": "p", "panes": [WS_SNAP["panes"][0]]}
        layout = layout_do_workspace(ws)
        self.assertIn("pane", layout)
        cmds = [s.get("command") for s in layout["pane"]["surfaces"]]
        self.assertTrue(any(c and "--resume 1111" in c for c in cmds))

    def test_layout_dois_panes_vira_split(self):
        layout = layout_do_workspace(WS_SNAP)
        self.assertEqual(layout["direction"], "horizontal")
        self.assertEqual(len(layout["children"]), 2)

    def test_layout_preserva_browser(self):
        layout = layout_do_workspace(WS_SNAP)
        segundo = layout["children"][1]["pane"]["surfaces"][0]
        self.assertEqual(segundo["type"], "browser")
        self.assertEqual(segundo["url"], "https://exemplo.com")

    def test_rebuild_so_planeja_workspace_ausente(self):
        dados = {"janelas": [{"uuid": "W", "ref": "window:1", "workspaces": [
            WS_SNAP, {"uuid": "S2", "ref": "workspace:2", "nome": "existente", "panes": []}]}]}
        estado = Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
            Workspace(uuid="S2", ref="workspace:2", nome="existente", panes=[])])])
        plano = planejar_rebuild(dados, estado)
        self.assertEqual([p["nome"] for p in plano], ["proj"])

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Rodar e confirmar a falha**

Run: `python3 -m unittest tests.unit.test_restore -v`
Expected: FAIL — `lib.restore` não existe.

- [ ] **Step 3: Implementar `lib/restore.py`**

```python
"""Sobe sessoes e reconstroi estrutura ausente."""
from typing import List
import json, shlex

from lib.cmux_state import rodar_cmux
from lib.bindings import comando_resume

def filtrar_alvo(itens: List[dict], alvo: str) -> List[dict]:
    if alvo == "all":
        return list(itens)
    return [i for i in itens if i.get("workspace") == alvo]

def _linha_comando(cwd: str, sessao: str) -> str:
    return "cd %s && %s" % (shlex.quote(cwd or "~"), " ".join(comando_resume(sessao)))

def subir(item: dict) -> bool:
    """Envia o comando para a aba. Funciona mesmo em aba nao materializada
    (o cmux enfileira e executa quando ela abre)."""
    payload = json.dumps({"workspace_id": item["ws_uuid"], "surface_id": item["surface"],
                          "text": _linha_comando(item.get("cwd"), item["sessao"]) + "\n"})
    saida = rodar_cmux("rpc", "surface.send_text", payload)
    return "surface_ref" in saida or "queued" in saida

def layout_do_workspace(ws: dict) -> dict:
    panes = []
    for p in ws["panes"]:
        surfaces = []
        for a in p["abas"]:
            if a.get("tipo") == "browser":
                surfaces.append({"type": "browser", "url": a.get("url", "about:blank")})
            elif a.get("sessao"):
                surfaces.append({"type": "terminal",
                                 "command": _linha_comando(a.get("cwd"), a["sessao"])})
            else:
                surfaces.append({"type": "terminal"})
        panes.append({"pane": {"surfaces": surfaces}})
    if len(panes) == 1:
        return panes[0]
    # o CLI nao expoe a proporcao real do split; 50/50 e' aproximacao documentada
    return {"direction": "horizontal", "split": 0.5, "children": panes}

def planejar_rebuild(dados: dict, estado) -> List[dict]:
    existentes = {w.nome for j in estado.janelas for w in j.workspaces}
    plano = []
    for j in dados["janelas"]:
        for w in j["workspaces"]:
            if w["nome"] in existentes:
                continue
            cwd = next((a.get("cwd") for p in w["panes"] for a in p["abas"] if a.get("cwd")), None)
            plano.append({"nome": w["nome"], "cwd": cwd, "layout": layout_do_workspace(w)})
    return plano

def criar_workspace(item: dict) -> bool:
    args = ["new-workspace", "--name", item["nome"], "--focus", "false",
            "--layout", json.dumps(item["layout"])]
    if item.get("cwd"):
        args += ["--cwd", item["cwd"]]
    return "workspace" in rodar_cmux(*args)
```

- [ ] **Step 4: Ligar ao `wake.py`**

Acrescentar aos argumentos:

```python
    ap.add_argument("--up", metavar="ALVO",
                    help="sobe as sessoes dormindo ('all' ou nome de workspace)")
    ap.add_argument("--rebuild", action="store_true",
                    help="recria workspaces ausentes a partir do snapshot")
```

E, antes do `return 0`, acrescentar:

```python
    if args.up:
        alvos = filtrar_alvo(r["dormindo"], args.up)
        ok = sum(1 for i in alvos if subir(i))
        print("\n  Subindo %d sessoes… %d enviadas." % (len(alvos), ok))

    if args.rebuild:
        plano = planejar_rebuild(dados, ler_estado())
        if not plano:
            print("\n  Nada a reconstruir: todos os workspaces existem.")
        else:
            for p in plano:
                marca = "ok" if criar_workspace(p) else "falhou"
                print("      %-28s %s" % (p["nome"][:28], marca))
            print("\n  %d workspaces recriados." % len(plano))
```

Acrescentar ao topo: `from lib.restore import filtrar_alvo, subir, planejar_rebuild, criar_workspace`

- [ ] **Step 5: Rodar testes e conferir o help**

Run:
```bash
bash tests/run-tests.sh
python3 scripts/wake.py --help
```
Expected: 37 testes PASS; help mostra `--up`, `--rebuild`, `--snapshot`, `--max-age`.

- [ ] **Step 6: Commit**

```bash
git add plugins/cmux-hibernate/scripts/lib/restore.py plugins/cmux-hibernate/scripts/wake.py plugins/cmux-hibernate/tests/unit/test_restore.py
git commit -m "feat(cmux-hibernate): sobe sessoes sob demanda e reconstroi workspaces ausentes"
```

---

### Task 10: Skill, documentação e registro no marketplace

**Files:**
- Create: `plugins/cmux-hibernate/skills/cmux-hibernate/SKILL.md`
- Create: `plugins/cmux-hibernate/README.md`
- Create: `plugins/cmux-hibernate/CHANGELOG.md`
- Modify: `.claude-plugin/marketplace.json`

**Interfaces:**
- Consumes: `hibernate.py` e `wake.py` (Tasks 6–9).
- Produces: skill invocável e plugin instalável.

- [ ] **Step 1: Escrever a SKILL.md**

```markdown
---
name: cmux-hibernate
description: Use quando o usuário quiser fechar o cmux para liberar memória ou reiniciar a máquina sem perder as sessões do Claude Code abertas, e quando quiser conferir ou restaurar o ambiente depois de reabrir. Cobre "vou fechar o cmux", "a máquina está travando", "será que voltou tudo?".
---

# cmux-hibernate

Hiberna as sessões Claude Code espalhadas pelos workspaces do cmux e as traz de
volta, sem recriar o consumo de memória que motivou o fechamento.

## Antes de fechar o cmux

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hibernate.py"          # dry-run: mostra o que faria
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/hibernate.py" --apply  # desarma e grava o snapshot
```

Sempre rode o dry-run primeiro e mostre o resultado ao usuário. O `--apply` **muta**
os bindings do cmux.

A aba de onde o comando roda é preservada — ela é a única que sobe quando o cmux
reabre, e é de onde a conferência pode ser pedida. Use `--all` apenas se o usuário
quiser zero sessões vivas.

## Depois de reabrir

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wake.py"              # confere
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wake.py" --up all     # sobe tudo
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/wake.py" --rebuild    # recria o que sumiu
```

No caminho normal nada é preciso: cada aba acorda quando o usuário a abre.

## Ao interpretar a saída

- **dormindo** é o estado saudável depois de hibernar, não um problema.
- **ausentes** significa que a aba não existe mais na estrutura — candidata a `--rebuild`.
- **sem transcript** não é recuperável; o histórico não existe mais em disco. Diga isso
  claramente em vez de sugerir tentativas.
```

- [ ] **Step 2: Escrever o README**

```markdown
# cmux-hibernate

Feche o cmux quando quiser — para reiniciar a máquina ou liberar memória — e reabra
com o ambiente intacto e leve.

## O problema

Dezenas de abas com sessões do Claude Code consomem memória. Fechar o cmux é
arriscado: o `resumeBinding` que ele usa para restaurar registra a *intenção* de um
hook, não o processo real, e envelhece quando uma sessão passa a gravar sob outro ID.
Além disso, reabrir sobe tudo de uma vez, recriando o peso que motivou o fechamento.

## Como funciona

`hibernate` lê o estado **dos processos** (`CMUX_SURFACE_ID`, `lsof`), não dos
metadados do cmux, e reescreve cada binding com o diretório correto e
`auto_resume: false`. Você fecha; ao reabrir, a estrutura volta e nada sobe. Cada aba
acorda quando você a abre.

O snapshot é um **retrato datado de uso único** — não há registro contínuo para
conciliar nem lista de sessões mortas para limpar. Os 5 últimos são mantidos; os
demais somem sozinhos.

## Uso

    python3 scripts/hibernate.py            # dry-run
    python3 scripts/hibernate.py --apply    # desarma e grava o snapshot
    # Cmd+Q, reabrir o cmux
    python3 scripts/wake.py                 # confere
    python3 scripts/wake.py --up all        # sobe tudo (opcional)
    python3 scripts/wake.py --rebuild       # recria workspaces ausentes

A aba de onde o `hibernate` roda é preservada: é a única sessão viva ao reabrir, e de
onde você pode pedir a conferência. `--all` desarma inclusive ela.

## Limitações conhecidas

- **Splits aproximados no `--rebuild`.** O CLI do cmux não expõe a proporção real dos
  painéis; a reconstrução assume 50/50. Só afeta workspaces com painel dividido, e só
  no modo de resgate.
- **Sessões sem transcript não voltam.** Se o `.jsonl` não existe mais em disco, não há
  o que retomar — o comando diz isso explicitamente em vez de tentar.
- **Específico do cmux.** Depende do CLI e de `CMUX_SURFACE_ID`.

## Requisitos

Python 3.9+ (somente stdlib), macOS com cmux instalado.
```

- [ ] **Step 3: Escrever o CHANGELOG**

```markdown
# Changelog

## [0.1.0] — 2026-08-04

### Added
- `hibernate.py`: retrata o estado real, desarma os bindings preservando a aba de
  controle e grava snapshot + inventário em `~/.local/state/cmux-hibernate/`.
- `wake.py`: compara snapshot com o estado real; `--up` sobe sessões sob demanda e
  `--rebuild` recria workspaces ausentes.
- `lib/cmux_state.py`: deriva o vínculo sessão↔aba de `CMUX_SURFACE_ID`, tratando o
  `resumeBinding` apenas como complemento.
- Skill `cmux-hibernate` e registro no marketplace.
- 37 testes, incluindo regressão para binding desatualizado e para sessão duplicada.

### Notas de design
- Sem hooks e sem registro contínuo: o estado é derivado no momento do comando, com o
  cmux vivo. Um registro que afirma "estas sessões existem" apodrece; um retrato
  datado, não.
- Desarmar é via de mão única — o CLI do cmux não escreve `auto_resume: true`. Por isso
  a aba de controle é escolhida no `hibernate`, não depois.

### Em aberto
- Comportamento do cmux ao abrir uma aba com `auto_resume: false`: oferece restaurar ou
  devolve shell? Ver validação manual V2 no plano de implementação.
```

- [ ] **Step 4: Registrar no marketplace**

Acrescentar ao array `plugins` de `.claude-plugin/marketplace.json`:

```json
{
  "name": "cmux-hibernate",
  "source": "./plugins/cmux-hibernate",
  "description": "Hibernate and restore Claude Code sessions across cmux workspaces, freeing memory without losing your environment.",
  "version": "0.1.0",
  "license": "MIT",
  "category": "productivity",
  "keywords": ["cmux", "session", "restore", "hibernate", "memory"]
}
```

- [ ] **Step 5: Validar o JSON e rodar a suíte**

Run:
```bash
python3 -c "import json;json.load(open('.claude-plugin/marketplace.json'));print('marketplace.json OK')"
bash plugins/cmux-hibernate/tests/run-tests.sh
```
Expected: `marketplace.json OK` e 37 testes PASS.

- [ ] **Step 6: Commit**

```bash
git add plugins/cmux-hibernate/skills plugins/cmux-hibernate/README.md plugins/cmux-hibernate/CHANGELOG.md .claude-plugin/marketplace.json
git commit -m "docs(cmux-hibernate): adiciona skill, documentacao e registro no marketplace"
```

---

## Validação manual (requer o usuário)

Estes passos não podem ser automatizados — exigem fechar e reabrir o cmux. São o item §9.1
do spec, e a resposta define se o `wake` é essencial ou apenas conveniente.

- [ ] **V1: Ciclo completo.** Rodar `hibernate.py --apply`, dar `Cmd+Q`, reabrir o cmux.
- [ ] **V2: A pergunta em aberto.** Abrir uma aba desarmada. O cmux **oferece restaurar** ou
      devolve um shell? Anotar a resposta no `CHANGELOG.md` e no §9 do spec.
- [ ] **V3: Conferência.** Rodar `wake.py` e verificar se a contagem bate com o snapshot.
- [ ] **V4: Memória.** Comparar o consumo antes do `Cmd+Q` e depois de reabrir. É a métrica
      que justifica o plugin existir.

Se em V2 o cmux oferecer restaurar, registrar no README que o `--up` é opcional no
caminho feliz.
