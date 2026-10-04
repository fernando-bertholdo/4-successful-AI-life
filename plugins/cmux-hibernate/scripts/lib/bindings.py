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


def abas_que_casam(estado, alvo: str) -> list:
    """As abas cujo uuid (o formato do CMUX_SURFACE_ID) ou ref `surface:N` e' o alvo.
    Quem chama exige exatamente uma; alvo vazio nao casa com nada."""
    alvo = alvo.strip()
    if not alvo:
        return []
    return [a for *_, a in estado.todas_abas()
            if a.uuid.upper() == alvo.upper() or a.ref == alvo.lower()]


def planejar_desarme(estado, aba_controle: Optional[str],
                     duplicadas: Optional[List[str]] = None,
                     so_aba: Optional[str] = None) -> List[dict]:
    """Monta o plano de desarme. Pula a aba de controle e sessoes duplicadas.

    Com so_aba (uuid), o plano tem so' aquela aba, mesmo que ela seja a de
    controle: pedir a aba pelo nome e' o que permite a uma sessao hibernar a
    propria aba, como no revezamento."""
    proibidas = set(duplicadas or [])
    plano = []
    for janela, ws, _pane, aba in estado.todas_abas():
        if not aba.sessao or aba.sessao in proibidas:
            continue
        if so_aba is not None:
            if aba.uuid != so_aba:
                continue
        elif aba.uuid == aba_controle:
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
