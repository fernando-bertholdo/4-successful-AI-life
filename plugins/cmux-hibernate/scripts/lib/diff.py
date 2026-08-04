"""Compara o snapshot com o estado real.

A chave e' sempre o session id. Titulo e posicao mentem: uma aba rotulada com o
nome de um projeto pode hospedar sessao de outro.
"""
from pathlib import Path
from typing import Optional, Tuple
import json
import time

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
    vivas_agora = {a.sessao for *_, a in estado.todas_abas()
                   if a.sessao and a.fonte == "processo"}
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
