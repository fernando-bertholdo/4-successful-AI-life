#!/usr/bin/env python3
"""Confere e restaura o ambiente cmux a partir de um snapshot de hibernacao.

Roda direto no terminal, sem depender de sessao Claude — precondicao do cenario
de resgate, em que nenhuma existe.
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.cmux_state import ler_estado  # noqa: E402
from lib.diff import MAX_SNAPSHOT_AGE, carregar_snapshot, comparar, idade_em_dias  # noqa: E402
from lib.restore import criar_workspace, filtrar_alvo, planejar_rebuild, subir  # noqa: E402
from lib.snapshot import BASE_ESTADO  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Restaura sessoes Claude Code no cmux.")
    ap.add_argument("--snapshot", type=Path, help="diretorio de um snapshot especifico")
    ap.add_argument("--max-age", type=float, default=MAX_SNAPSHOT_AGE)
    ap.add_argument("--up", metavar="ALVO",
                    help="sobe as sessoes dormindo ('all' ou nome de workspace)")
    ap.add_argument("--rebuild", action="store_true",
                    help="recria workspaces ausentes a partir do snapshot")
    args = ap.parse_args()

    try:
        dados, origem = carregar_snapshot(BASE_ESTADO, args.snapshot)
        estado = ler_estado()
    except RuntimeError as e:
        print("erro: %s" % e, file=sys.stderr)
        return 2

    idade = idade_em_dias(dados, time.time())
    print("Snapshot de %s (%.1f dias) · %s" % (dados["gerado_em"], idade, origem.name))
    if idade > args.max_age:
        resp = input("  Snapshot com mais de %.0f dias. Continuar? [s/N] " % args.max_age)
        if resp.strip().lower() not in ("s", "sim", "y"):
            return 1

    r = comparar(dados, estado)
    print("\n  rodando        %d" % len(r["vivas"]))
    print("  dormindo       %d  (sobem ao abrir a aba)" % len(r["dormindo"]))
    if r["ausentes"]:
        print("  ausentes       %d  (aba nao existe mais)" % len(r["ausentes"]))
        for x in r["ausentes"]:
            print("      %s  %s  ·  %s" % (x["sessao"][:8], x["workspace"], x["titulo"][:44]))
    if r["sem_transcript"]:
        print("  sem transcript %d  (nao restauraveis)" % len(r["sem_transcript"]))
    if not r["ausentes"] and not args.up and not args.rebuild:
        print("\n  Nada a corrigir.")

    if args.up:
        alvos = filtrar_alvo(r["dormindo"], args.up)
        ok = sum(1 for i in alvos if subir(i))
        print("\n  Subindo %d sessoes… %d enviadas." % (len(alvos), ok))

    if args.rebuild:
        plano = planejar_rebuild(dados, estado)
        if not plano:
            print("\n  Nada a reconstruir: todos os workspaces existem.")
        else:
            for p in plano:
                print("      %-28s %s" % (p["nome"][:28],
                                          "ok" if criar_workspace(p) else "falhou"))
            print("\n  %d workspaces processados." % len(plano))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
