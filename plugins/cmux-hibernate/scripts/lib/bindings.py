"""O comando de retomada e a escolha de uma aba pelo nome.

Ate' a 0.2.0 este modulo desarmava a aba reescrevendo o resumeBinding com
`cmux surface resume set --source agent-hook` e aceitava o `OK` do CLI como prova.
No cmux 0.65.2 essa escrita e' recusada em silencio, e o desarme passou a ser
encerrar o processo (lib/encerrar.py), conferido no autosave do cmux.
"""
from typing import List


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
