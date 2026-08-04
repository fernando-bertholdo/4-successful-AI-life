"""Serializacao e persistencia do snapshot de hibernacao.

O snapshot e' um retrato datado de uso unico: vale por um ciclo de fechar e
reabrir. Nenhum campo afirma estado volatil ("estava rodando"), porque isso
envelheceria em silencio — tudo que muda e' derivado na leitura.
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import json
import shutil

BASE_ESTADO = Path.home() / ".local" / "state" / "cmux-hibernate"


def _aba(a) -> dict:
    d = {"uuid": a.uuid, "ref": a.ref, "tipo": a.tipo, "titulo": a.titulo,
         "sessao": a.sessao, "cwd": a.cwd, "fonte": a.fonte,
         "transcript": a.transcript, "estagnada": a.estagnada}
    if a.url:
        d["url"] = a.url
    return d


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


def _inventario(d: dict) -> str:
    linhas = ["# Snapshot cmux-hibernate", "",
              "**Gerado:** " + d["gerado_em"], "",
              "Comandos de retomada manual, caso precise reconstruir sem agente:", ""]
    for j in d["janelas"]:
        for w in j["workspaces"]:
            abas = [a for p in w["panes"] for a in p["abas"] if a.get("sessao")]
            if not abas:
                continue
            linhas += ["## " + w["nome"], ""]
            for a in abas:
                marca = " *(estagnada)*" if a.get("estagnada") else ""
                linhas.append("- " + (a["titulo"] or "sem titulo")[:70] + marca)
                linhas.append("  ```")
                linhas.append("  cd '%s' && claude --resume %s --dangerously-skip-permissions"
                              % (a.get("cwd") or "~", a["sessao"]))
                linhas.append("  ```")
            linhas.append("")
    return "\n".join(linhas)


def gravar(dados: dict, base: Path = BASE_ESTADO) -> Path:
    destino = base / datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "snapshot.json").write_text(json.dumps(dados, indent=2, ensure_ascii=False))
    (destino / "INVENTARIO.md").write_text(_inventario(dados))
    return destino


def aplicar_retencao(base: Path, manter: int = 5) -> List[Path]:
    """Mantem so' os mais recentes. E' o que impede o acumulo de retratos velhos."""
    if not base.exists():
        return []
    dirs = sorted([d for d in base.iterdir() if d.is_dir()], reverse=True)
    removidos = dirs[manter:]
    for d in removidos:
        shutil.rmtree(d)
    return removidos
