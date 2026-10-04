#!/usr/bin/env python3
"""Hiberna as sessoes Claude Code do cmux: retrata, desarma e libera memoria.

O padrao e' dry-run. Use --apply para desarmar de fato.

Saida: 0 no caminho normal; 1 quando --surface nao desarma, ou nao desarmaria,
a aba pedida; 2 em erro de leitura do cmux ou de argumento.
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.bindings import abas_que_casam, desarmar, planejar_desarme  # noqa: E402
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
    escopo = ap.add_mutually_exclusive_group()
    escopo.add_argument("--all", action="store_true",
                        help="desarma tambem a aba de onde o comando foi chamado")
    escopo.add_argument("--surface", metavar="ABA",
                        help="desarma so' esta aba (uuid ou ref surface:N), "
                             "mesmo que seja a de onde o comando foi chamado")
    ap.add_argument("--stale-days", type=int, default=STALE_DAYS)
    args = ap.parse_args()

    try:
        estado = ler_estado()
    except RuntimeError as e:
        print("erro: %s" % e, file=sys.stderr)
        return 2

    so_aba = None
    if args.surface is not None:
        achadas = abas_que_casam(estado, args.surface)
        if len(achadas) != 1:
            print("erro: %s abas casam com %r; --surface pede exatamente uma"
                  % ("nenhuma" if not achadas else len(achadas), args.surface), file=sys.stderr)
            return 2
        aba = achadas[0]
        if not aba.sessao:
            print("erro: a aba %s nao tem sessao Claude Code" % aba.ref, file=sys.stderr)
            return 2
        so_aba = aba.uuid

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

    dados = serializar(estado, None if so_aba == controle else controle, args.stale_days)
    destino = gravar(dados, BASE_ESTADO)
    aplicar_retencao(BASE_ESTADO)

    plano = planejar_desarme(estado, controle, duplicadas, so_aba)
    if so_aba is not None:
        for p in plano:
            print("\n  Aba pedida: %s  %s" % (p["sessao"][:8], (p["titulo"] or "")[:58]))
        if not plano:
            print("\n  Aba pedida pulada: a sessao dela aparece em mais de uma aba.")
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
        falhou_pedida = so_aba is not None and ok == 0
        if so_aba is not None:
            print("  Preservadas: todas as outras (--surface)")
        else:
            print("  Preservada: %s" % ("nenhuma (--all)" if controle is None else "1 (esta aba)"))

    print("\n  Snapshot: %s" % destino)
    if so_aba is not None and (not plano or (args.apply and falhou_pedida)):
        print("  A aba pedida continua armada.", file=sys.stderr)
        return 1
    if args.apply:
        print("  Pode dar Cmd+Q.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
