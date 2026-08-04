#!/usr/bin/env python3
"""Hiberna as sessoes Claude Code do cmux: retrata, desarma e libera memoria.

O padrao e' dry-run. Use --apply para desarmar de fato.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.bindings import desarmar, planejar_desarme  # noqa: E402
from lib.cmux_state import (  # noqa: E402
    STALE_DAYS,
    _ps_eww,
    detectar_duplicatas,
    ler_estado,
    parse_processos,
)
from lib.snapshot import BASE_ESTADO, aplicar_retencao, gravar, serializar  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Hiberna sessoes Claude Code no cmux.")
    ap.add_argument("--apply", action="store_true",
                    help="desarma os bindings de fato (padrao: apenas retrata)")
    ap.add_argument("--all", action="store_true",
                    help="desarma tambem a aba de onde o comando foi chamado")
    ap.add_argument("--stale-days", type=int, default=STALE_DAYS)
    args = ap.parse_args()

    try:
        estado = ler_estado()
    except RuntimeError as e:
        print("erro: %s" % e, file=sys.stderr)
        return 2

    controle = None if args.all else os.environ.get("CMUX_SURFACE_ID")
    abas = [a for *_, a in estado.todas_abas() if a.sessao]
    estagnadas = [a for a in abas if a.estagnada]

    print("Estado real: %d sessoes em %d workspaces, %d janelas" % (
        len(abas),
        sum(len(j.workspaces) for j in estado.janelas),
        len(estado.janelas)))

    if estagnadas:
        print("\n  %d sem atividade ha mais de %d dias:" % (len(estagnadas), args.stale_days))
        for a in estagnadas:
            print("      %s  %s" % (a.sessao[:8], (a.titulo or "")[:58]))

    duplicadas = detectar_duplicatas(parse_processos(_ps_eww()))
    if duplicadas:
        print("\n  anomalia: %d sessoes aparecem em mais de uma aba; serao puladas"
              % len(duplicadas))

    dados = serializar(estado, controle, args.stale_days)
    destino = gravar(dados, BASE_ESTADO)
    aplicar_retencao(BASE_ESTADO)

    plano = planejar_desarme(estado, controle, duplicadas)
    if not args.apply:
        print("\n  Desarmaria %d abas (dry-run). Use --apply para valer." % len(plano))
    else:
        ok = 0
        for p in plano:
            if p["cwd"] and desarmar(p["janela"], p["workspace"], p["surface"],
                                     p["sessao"], p["cwd"]):
                ok += 1
            else:
                print("      falhou: %s  %s" % (p["sessao"][:8], (p["titulo"] or "")[:50]))
        print("\n  Desarmadas: %d abas   (sobem so quando voce abrir)" % ok)
        print("  Preservada: %s" % ("nenhuma (--all)" if controle is None else "1 (esta aba)"))

    print("\n  Snapshot: %s" % destino)
    if args.apply:
        print("  Pode dar Cmd+Q.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
