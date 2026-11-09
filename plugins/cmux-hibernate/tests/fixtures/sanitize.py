#!/usr/bin/env python3
"""Transforma a captura crua em fixture publicavel.

O repositorio e' publico. A captura crua carrega nomes de cliente, titulos de
conversa e caminhos de projeto reais. Este script substitui tudo isso por
equivalentes sinteticos, preservando exatamente a ESTRUTURA que os testes
exercitam: hierarquia, formato de UUID, tipos de surface, presenca de sessao.

A substituicao e' deterministica e injetora — dois identificadores diferentes
no cru continuam diferentes no sanitizado, senao os testes de vinculo perderiam
o sentido.

A linha do `ps eww` e' reconstruida por LISTA DE PERMISSAO, nao de bloqueio: sai
so' o argv que os parsers leem (binario, --resume/--session-id, a flag de
permissao, o marcador de daemon) e as variaveis de PERMITIDAS. Todo o resto do
ambiente (tokens do socket do cmux, TMPDIR, HOME, PATH, o argv codificado em
base64) fica de fora; o CMUX_AGENT_LAUNCH_ARGV_B64 e' recodificado a partir do
argv ja sintetico. Ate' 31/10/2026 a sanitizacao era por substituicao e deixou
passar um token de socket e o argv real em base64.

Uso: python3 sanitize.py
"""
from pathlib import Path
import base64
import getpass
import re
import socket

DIR = Path(__file__).resolve().parent
RAW = DIR / ".raw"

RE_UUID_MAI = re.compile(r"\b[0-9A-F]{8}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{4}-[0-9A-F]{12}\b")
RE_UUID_MIN = re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")
RE_TITULO = re.compile(r'"([^"]*)"')
RE_PATH = re.compile(r"/Users/[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]*")


class Mapa:
    """Substituicao deterministica e injetora: cada original ganha um sintetico."""

    def __init__(self, molde):
        self.molde = molde
        self._visto = {}

    def de(self, original):
        if original not in self._visto:
            self._visto[original] = self.molde(len(self._visto))
        return self._visto[original]


def uuid_maiusculo(i):
    return "{:08X}-0000-4000-8000-{:012X}".format(i + 0xA0000000, i)


def uuid_minusculo(i):
    return "{:08x}-0000-4000-8000-{:012x}".format(i + 0x50000000, i)


def caminho(i):
    return "/Users/dev/projects/proj-{}".format(i)


# Caminhos estruturais: identificam o binario e a arvore de dados do Claude Code.
# Nao carregam informacao sensivel e os parsers dependem deles — preservar.
ESTRUTURAIS = (".local/bin/claude", ".local/share/claude", ".claude/")


def substituir_caminho(m, mapa):
    original = m.group(0)
    if any(marca in original for marca in ESTRUTURAIS):
        # troca so o nome do usuario, mantendo o resto do caminho intacto
        return re.sub(r"^/Users/[A-Za-z0-9_.-]+", "/Users/dev", original)
    return mapa.de(original)


def sanitizar_titulo(texto, mapa_ws):
    """Preserva o formato do titulo, troca o conteudo."""
    if not texto:
        return texto
    # prompt de shell: user@host:~/caminho
    if "@" in texto and ":" in texto:
        return "dev@devbox:~/projects/proj-x"
    # titulo de sessao Claude (comeca com marcador de atividade)
    for marcador in ("✳", "⠂", "⠐", "◉"):
        if texto.startswith(marcador):
            return "{} tarefa {}".format(marcador, mapa_ws.de(texto).rsplit("-", 1)[-1])
    if texto.endswith(".md"):
        return "documento.md"
    if texto.startswith("http"):
        return "https://exemplo.com/pagina"
    return "workspace {}".format(mapa_ws.de(texto).rsplit("-", 1)[-1])


PERMITIDAS = ("CMUX_SURFACE_ID", "CMUX_WORKSPACE_ID", "CMUX_AGENT_LAUNCH_KIND")
KINDS = {"claude", "codex"}
_RE_SESSAO = re.compile(r"--(resume|session-id)\s+(\S+)")


def sanitizar_ps(linha, mai, mino):
    """Uma linha `<pid> <command + environment>` reconstruida so' com o permitido."""
    pid = linha.split()[0]
    argv = ["/Users/dev/.local/bin/claude"]
    if " daemon run" in linha:
        argv += ["daemon", "run"]
    for marca in ("bg-pty-host", "bg-spare"):
        if marca in linha:
            argv.append(marca)
    m = _RE_SESSAO.search(linha)
    if m:
        valor = m.group(2)
        argv += ["--" + m.group(1),
                 mino.de(valor) if RE_UUID_MIN.fullmatch(valor) else "titulo-sintetico"]
    if "--dangerously-skip-permissions" in linha:
        argv.append("--dangerously-skip-permissions")
    env = []
    for nome in PERMITIDAS:
        v = re.search(r"(?:^|\s)%s=(\S+)" % nome, linha)
        if not v:
            continue
        valor = v.group(1)
        if RE_UUID_MAI.fullmatch(valor):
            env.append("%s=%s" % (nome, mai.de(valor)))
        elif nome == "CMUX_AGENT_LAUNCH_KIND" and valor in KINDS:
            env.append("%s=%s" % (nome, valor))
    if "CMUX_AGENT_LAUNCH_ARGV_B64=" in linha:
        b64 = base64.b64encode("\0".join(argv).encode()).decode()
        env.append("CMUX_AGENT_LAUNCH_ARGV_B64=" + b64)
    return " ".join([pid] + argv + env)


def main():
    if not RAW.exists():
        raise SystemExit("nada em .raw/ — rode capture.sh antes")

    mai, mino, paths = Mapa(uuid_maiusculo), Mapa(uuid_minusculo), Mapa(caminho)
    rotulos = Mapa(lambda i: "rotulo-{}".format(i))

    for nome in ("tree.txt", "ps-eww.txt"):
        origem = RAW / nome
        if not origem.exists():
            continue
        texto = origem.read_text(errors="ignore")
        if nome == "ps-eww.txt":
            # reconstruida do zero: nao passa pelas substituicoes da arvore
            texto = "\n".join(sanitizar_ps(l, mai, mino) for l in texto.splitlines()
                              if l.strip()) + "\n"
        else:
            texto = RE_UUID_MAI.sub(lambda m: mai.de(m.group(0)), texto)
            texto = RE_UUID_MIN.sub(lambda m: mino.de(m.group(0)), texto)
            texto = RE_TITULO.sub(
                lambda m: '"{}"'.format(sanitizar_titulo(m.group(1), rotulos)), texto)
            texto = RE_PATH.sub(lambda m: substituir_caminho(m, paths), texto)
        # varredura final: usuario e host da maquina, lidos do ambiente para nao
        # ficarem hardcoded num repositorio publico
        texto = texto.replace(getpass.getuser(), "dev")
        host = socket.gethostname().split(".")[0]
        texto = texto.replace(host, "devbox")
        if host.endswith("-MacBook") or "-" in host:
            texto = texto.replace(host.split("-")[0], "dev")

        (DIR / nome).write_text(texto)
        print("  {} -> {} linhas".format(nome, len(texto.splitlines())))

    print("\nfixtures sanitizadas. Confira antes de commitar:")
    print("  grep -inE \"$(whoami)|$(hostname -s)|/Documents/|/var/folders\" {}/*.txt".format(DIR))
    print("  bash ../run-tests.sh   # test_sanitize.py reprova ambiente real nas fixtures")


if __name__ == "__main__":
    main()
