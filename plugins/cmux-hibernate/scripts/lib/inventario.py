"""Completa o estado com as abas que tem sessao Claude Code mas nao tem processo.

O processo (`CMUX_SURFACE_ID`) so' enxerga quem esta rodando. Ficavam de fora a aba
armada cujo restore falhou e a aba que ja dormia de um ciclo anterior, e hibernar duas
vezes seguidas apagava esta do inventario. Duas fontes a mais, nesta ordem:

    autosave do cmux        -> painel com agent ou binding (a fonte que o restore le)
    snapshot do --apply anterior -> quem ja dormia, pela aba que ainda existe

O processo continua vencendo as duas.
"""
from pathlib import Path
from typing import Dict, Optional

from lib.cmux_state import RAIZ_PROJETOS, Estado, anexar_transcript


def _abas_do_snapshot(dados: dict):
    for j in dados.get("janelas", []):
        for w in j.get("workspaces", []):
            for p in w.get("panes", []):
                for a in p.get("abas", []):
                    if a.get("sessao") and a.get("uuid"):
                        yield a


def completar_inventario(estado: Estado, paineis: Dict, anterior: Optional[dict],
                         raiz: Path = RAIZ_PROJETOS) -> Dict[str, int]:
    """Preenche sessao, cwd, fonte e armada. Devolve quantas abas cada fonte trouxe."""
    do_anterior = {a["uuid"].upper(): a for a in _abas_do_snapshot(anterior or {})}
    n = {"autosave": 0, "snapshot": 0}
    for *_, aba in estado.todas_abas():
        painel = paineis.get(aba.uuid.upper())
        if painel is not None:
            aba.armada = painel.armado
        if aba.sessao:
            continue
        # claude vivo na aba sem id no argv: o pid vem junto, para o plano o encerrar
        # em vez de limpar o registro com o processo de pe (o proximo turno rearmaria)
        aba.pid = aba.pid or estado.processos.get(aba.uuid)
        if painel is not None and painel.sessao:
            aba.sessao, aba.fonte = painel.sessao, "autosave"
            aba.cwd = aba.cwd or painel.cwd
            n["autosave"] += 1
        elif aba.uuid.upper() in do_anterior:
            velha = do_anterior[aba.uuid.upper()]
            aba.sessao, aba.fonte = velha["sessao"], "snapshot"
            aba.cwd = aba.cwd or velha.get("cwd")
            n["snapshot"] += 1
        else:
            continue
        anexar_transcript(aba, raiz)
    return n
