"""Escrita de resumeBinding no cmux.

Nota de arquitetura: o CLI do cmux grava sempre auto_resume=false — o valor
true e' privilegio do hook interno, que so' o escreve quando uma sessao tem
atividade. Nao existe "rearmar" depois. Desarmar e' via de mao unica, e por
isso a aba de controle precisa ser escolhida no momento do hibernate.
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
