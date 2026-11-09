"""Compara o snapshot com o estado real.

A chave e' sempre o session id. Titulo e posicao mentem: uma aba rotulada com o
nome de um projeto pode hospedar sessao de outro.
"""
from pathlib import Path
from typing import Dict, Optional, Tuple
import json

from lib.carimbo import ler, mais_recentes_primeiro

MAX_SNAPSHOT_AGE = 3


def _aplicados(base: Path, aceita_sem_tipo: bool = False):
    """Os snapshots de --apply, do mais recente ao mais antigo. Dry-run fica fora, e o
    snapshot sem tipo (gravado ate' a 0.2.0, quando dry-run e --apply nao se distinguiam)
    so' entra com aceita_sem_tipo."""
    if not base.exists():
        return
    for d in mais_recentes_primeiro([d for d in base.iterdir() if (d / "snapshot.json").exists()]):
        try:
            dados = json.loads((d / "snapshot.json").read_text())
        except (OSError, ValueError):
            continue
        if dados.get("tipo") == "apply" or (aceita_sem_tipo and "tipo" not in dados):
            yield dados, d


def carregar_snapshot(base: Path, escolhido: Optional[Path] = None) -> Tuple[dict, Path]:
    if escolhido:
        try:
            return json.loads((escolhido / "snapshot.json").read_text()), escolhido
        except (OSError, ValueError) as e:
            raise RuntimeError("nao li o snapshot em %s (%s)" % (escolhido, e))
    for dados, d in _aplicados(base):
        return dados, d
    raise RuntimeError("nenhum snapshot de --apply em %s — rode o hibernate --apply antes "
                       "(snapshot de dry-run ou da 0.2.0 so' com --snapshot <dir>)" % base)


def ultimo_apply(base: Path) -> Optional[dict]:
    for dados, _ in _aplicados(base):
        return dados
    return None


def ultimo_para_inventario(base: Path) -> Optional[dict]:
    """De onde o hibernate tira quem ja dormia: o ultimo --apply, ou o da 0.2.0, sem tipo.
    So' serve para lembrar a sessao de uma aba sem processo; nao entra na comparacao."""
    for dados, _ in _aplicados(base, aceita_sem_tipo=True):
        return dados
    return None


def idade_em_dias(dados: dict, agora: float) -> float:
    return (agora - ler(dados["gerado_em"]).timestamp()) / 86400.0


def _abas_do_snapshot(dados: dict):
    for j in dados["janelas"]:
        for w in j["workspaces"]:
            for p in w["panes"]:
                for a in p["abas"]:
                    if a.get("sessao"):
                        yield j, w, a


SUBIU_JUNTO = 60  # s: processo nascido ate' isso depois do cmux subiu com o restore
DORMIR = {"encerrar", "limpar", "dormindo"}


def comparar(dados: dict, estado, armadas: Optional[Dict[str, str]] = None,
             inicios: Optional[Dict[str, float]] = None,
             inicio_cmux: Optional[float] = None) -> dict:
    """Classifica cada aba do snapshot contra o estado real e, se houver, contra o plano.

    Com o plano de um --apply (0.3.0), a aba planejada para dormir e' "dormindo" (sem
    processo e sem registro armado), "subiu_sozinha" (processo nascido junto com o cmux:
    o desarme falhou), "acordada" (processo nascido bem depois: alguem a abriu),
    "nao_dormiu" (processo anterior ao snapshot), "suspeita" (nasceu tarde, mas o hibernate
    nao a conferiu desarmada) ou "armada" (sem processo, mas sobe no proximo fechamento).
    Sem plano, como ate' a 0.2.0: vivas, dormindo, ausentes."""
    armadas, inicios = armadas or {}, inicios or {}
    plano = {p["surface"]: p for p in dados.get("plano") or []}
    gerado = ler(dados["gerado_em"]).timestamp() if dados.get("gerado_em") else None
    atuais = {a.uuid: a for *_, a in estado.todas_abas()}
    vivas_agora = {a.sessao for a in atuais.values() if a.sessao and a.fonte == "processo"}
    r = {k: [] for k in ("vivas", "dormindo", "ausentes", "sem_transcript", "subiu_sozinha",
                         "acordada", "suspeita", "nao_dormiu", "controle", "armada")}
    for j, w, a in _abas_do_snapshot(dados):
        item = {"sessao": a["sessao"], "titulo": a.get("titulo", ""), "cwd": a.get("cwd"),
                "workspace": w["nome"], "janela": j["uuid"], "ws_uuid": w["uuid"],
                "surface": a["uuid"], "ref": a.get("ref")}
        atual = atuais.get(a["uuid"])
        pid = (atual.pid or estado.processos.get(a["uuid"])) if atual is not None else None
        viva = pid is not None or a["sessao"] in vivas_agora
        acao = (plano.get(a["uuid"]) or {}).get("acao")
        resultado = (plano.get(a["uuid"]) or {}).get("resultado") or {}
        conferida = resultado.get("verificado")
        if not a.get("transcript"):
            r["sem_transcript"].append(item)
        elif atual is None:
            r["ausentes"].append(item)
        elif acao == "controle":
            item["viva"] = viva
            r["controle"].append(item)
        elif acao in DORMIR and viva:
            ini = inicios.get(pid) if pid else None
            item["hora"] = ini
            if ini is None or inicio_cmux is None:
                r["subiu_sozinha"].append(item)
            elif gerado is not None and ini < gerado:
                r["nao_dormiu"].append(item)
            elif ini - inicio_cmux <= SUBIU_JUNTO:
                r["subiu_sozinha"].append(item)
            elif conferida is False:
                # o hibernate nao conferiu esta aba: o processo tardio pode ser o restore
                # atrasado. O ambiente nao separa os dois: CMUX_AGENT_RESUME_LAUNCH=1 sai
                # de todo `claude --resume <id>` pelo wrapper do cmux, digitado ou nao.
                r["suspeita"].append(item)
            else:
                r["acordada"].append(item)
        elif viva:
            r["vivas"].append(item)
        elif a["uuid"].upper() in armadas:
            item["armada"] = armadas[a["uuid"].upper()]
            r["armada"].append(item)
        else:
            r["dormindo"].append(item)
    return r
