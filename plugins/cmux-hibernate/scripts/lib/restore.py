"""Sobe sessoes sob demanda e reconstroi estrutura ausente."""
from typing import List
import json
import shlex

from lib.bindings import comando_resume
from lib.cmux_state import rodar_cmux


def filtrar_alvo(itens: List[dict], alvo: str) -> List[dict]:
    if alvo == "all":
        return list(itens)
    return [i for i in itens if i.get("workspace") == alvo]


def _linha_comando(cwd: str, sessao: str) -> str:
    return "cd %s && %s" % (shlex.quote(cwd or "~"), " ".join(comando_resume(sessao)))


def subir(item: dict) -> bool:
    """Envia o comando para a aba.

    Funciona mesmo em aba ainda nao materializada: o cmux enfileira o texto
    (queued: true) e executa quando ela e' aberta.
    """
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
    # O CLI nao expoe a proporcao real do split; 50/50 e' aproximacao documentada.
    return {"direction": "horizontal", "split": 0.5, "children": panes}


def planejar_rebuild(dados: dict, estado) -> List[dict]:
    """So' planeja workspaces que nao existem — nunca duplica o que voltou."""
    existentes = {w.nome for j in estado.janelas for w in j.workspaces}
    plano = []
    for j in dados["janelas"]:
        for w in j["workspaces"]:
            if w["nome"] in existentes:
                continue
            cwd = next((a.get("cwd") for p in w["panes"] for a in p["abas"] if a.get("cwd")),
                       None)
            plano.append({"nome": w["nome"], "cwd": cwd, "layout": layout_do_workspace(w)})
    return plano


def criar_workspace(item: dict) -> bool:
    args = ["new-workspace", "--name", item["nome"], "--focus", "false",
            "--layout", json.dumps(item["layout"])]
    if item.get("cwd"):
        args += ["--cwd", item["cwd"]]
    return "workspace" in rodar_cmux(*args)
