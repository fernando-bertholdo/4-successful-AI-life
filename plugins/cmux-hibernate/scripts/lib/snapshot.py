"""Serializacao e persistencia do snapshot de hibernacao.

O snapshot e' um retrato datado de uso unico: vale por um ciclo de fechar e
reabrir. Nas abas, nenhum campo afirma estado volatil ("estava rodando"), porque
isso envelheceria em silencio — tudo que muda e' derivado na leitura. O que o
--apply fez fica em `plano`, aba a aba, com o resultado conferido e a hora: e' contra
ele que o wake compara.

So' o --apply entra na retencao dos 5. O dry-run vai para `ultimo-dry-run/`, que
cada dry-run sobrescreve e que nem a retencao nem o wake escolhem.
"""
from pathlib import Path
from typing import List, Optional
import json
import shlex
import shutil

from lib.carimbo import (agora_utc, instante_do_nome, ler, mais_recentes_primeiro, mostrar,
                         nome_de_diretorio)

BASE_ESTADO = Path.home() / ".local" / "state" / "cmux-hibernate"
NOME_DRY_RUN = "ultimo-dry-run"
_PLUGIN_JSON = Path(__file__).resolve().parents[2] / ".claude-plugin" / "plugin.json"


def versao_do_plugin() -> Optional[str]:
    try:
        return json.loads(_PLUGIN_JSON.read_text()).get("version")
    except (OSError, ValueError):
        return None


def _aba(a) -> dict:
    d = {"uuid": a.uuid, "ref": a.ref, "tipo": a.tipo, "titulo": a.titulo,
         "sessao": a.sessao, "cwd": a.cwd, "fonte": a.fonte,
         "transcript": a.transcript, "estagnada": a.estagnada}
    if a.url:
        d["url"] = a.url
    return d


def serializar(estado, aba_controle: Optional[str], stale_days: int, tipo: str = "dry-run",
               plano: Optional[List[dict]] = None, escopo: Optional[str] = None,
               versao_cmux: Optional[str] = None) -> dict:
    return {
        "gerado_em": agora_utc(),
        "tipo": tipo,
        "versao_plugin": versao_do_plugin(),
        "versao_cmux": versao_cmux,
        "escopo": escopo,
        "metodo": "CMUX_SURFACE_ID (processo) + autosave do cmux",
        "stale_days": stale_days,
        "aba_de_controle": aba_controle,
        "plano": plano or [],
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
              "**Gerado:** %s (%s)" % (mostrar(d["gerado_em"]), d["gerado_em"]), "",
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
                cwd = shlex.quote(a["cwd"]) if a.get("cwd") else "~"
                linhas.append("  cd %s && claude --resume %s --dangerously-skip-permissions"
                              % (cwd, shlex.quote(a["sessao"])))
                linhas.append("  ```")
            linhas.append("")
    return "\n".join(linhas)


def gravar(dados: dict, base: Path = BASE_ESTADO, nome: Optional[str] = None) -> Path:
    destino = base / (nome or nome_de_diretorio(ler(dados["gerado_em"])))
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "snapshot.json").write_text(json.dumps(dados, indent=2, ensure_ascii=False))
    (destino / "INVENTARIO.md").write_text(_inventario(dados))
    return destino


def gravar_dry_run(dados: dict, base: Path = BASE_ESTADO) -> Path:
    """Sobrescreve `ultimo-dry-run/`: fora da retencao, para nao empurrar um --apply."""
    destino = base / NOME_DRY_RUN
    if destino.exists():
        shutil.rmtree(destino)
    return gravar(dados, base, NOME_DRY_RUN)


def aplicar_retencao(base: Path, manter: int = 5) -> List[Path]:
    """Mantem so' os mais recentes. E' o que impede o acumulo de retratos velhos.
    Diretorio cujo nome nao e' carimbo de snapshot nao entra na conta nem e' apagado."""
    if not base.exists():
        return []
    dirs = mais_recentes_primeiro([d for d in base.iterdir()
                                   if d.is_dir() and instante_do_nome(d.name) is not None])
    removidos = dirs[manter:]
    for d in removidos:
        shutil.rmtree(d)
    return removidos
