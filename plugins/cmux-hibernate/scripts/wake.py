#!/usr/bin/env python3
"""Confere e restaura o ambiente cmux a partir do snapshot do ultimo --apply.

Compara aba a aba o plano do hibernate com o estado real: processos, o instante em
que cada um nasceu e o autosave do cmux. Roda direto no terminal, sem depender de
sessao Claude — precondicao do cenario de resgate, em que nenhuma existe —, e roda
sem terminal interativo, que e' como o agente o chama.

Saida: 0 sem falha; 1 com alguma FALHA (subiu sozinha, nao dormiu, suspeita, ou a aba
de controle que nao subiu); 2 em erro de leitura ou de argumento.
"""
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.autosave import ler_autosave  # noqa: E402
from lib.carimbo import BRASILIA, ler, mostrar  # noqa: E402
from lib.cmux_state import inicio_do_cmux, inicios_de, ler_estado  # noqa: E402
from lib.diff import MAX_SNAPSHOT_AGE, carregar_snapshot, comparar, idade_em_dias  # noqa: E402
from lib.restore import criar_workspace, filtrar_alvo, planejar_rebuild, subir  # noqa: E402
from lib.snapshot import BASE_ESTADO  # noqa: E402

RESTORE_EM_CURSO = 120  # s depois de o cmux abrir em que o restore ainda pode estar rodando


def _hora(epoch) -> str:
    return datetime.fromtimestamp(epoch, BRASILIA).strftime("%H:%M BRT") if epoch else "?"


def _listar(itens, sufixo=None):
    for x in itens:
        print("      %s  %s  ·  %s%s" % (x["sessao"][:8], x["workspace"][:24], x["titulo"][:44],
                                         sufixo(x) if sufixo else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description="Confere e restaura sessoes Claude Code no cmux.")
    ap.add_argument("--snapshot", type=Path, help="diretorio de um snapshot especifico")
    ap.add_argument("--estado", type=Path, default=BASE_ESTADO, metavar="DIR",
                    help="diretorio dos snapshots (padrao: %(default)s)")
    ap.add_argument("--max-age", type=float, default=MAX_SNAPSHOT_AGE)
    ap.add_argument("--up", metavar="ALVO",
                    help="retoma as sessoes sem processo ('all' ou nome de workspace)")
    ap.add_argument("--rebuild", action="store_true",
                    help="recria workspaces ausentes a partir do snapshot")
    args = ap.parse_args()

    try:
        dados, origem = carregar_snapshot(args.estado, args.snapshot)
        estado = ler_estado()
    except RuntimeError as e:
        print("erro: %s" % e, file=sys.stderr)
        return 2
    try:
        _, paineis = ler_autosave()
        armadas = {u: p.armado for u, p in paineis.items() if p.armado}
    except RuntimeError as e:
        print("aviso: %s; 'armada' nao foi conferida" % e, file=sys.stderr)
        armadas = None
    pids = {a.pid for *_, a in estado.todas_abas() if a.pid} | set(estado.processos.values())
    pids = sorted(pids)
    inicios, cmux = inicios_de(pids), inicio_do_cmux()

    idade = idade_em_dias(dados, time.time())
    print("Snapshot de %s (%.1f dias) · %s · %s" % (
        mostrar(dados["gerado_em"]), idade, origem.name, dados.get("tipo") or "sem tipo (0.2.0)"))
    if idade > args.max_age:
        if sys.stdin.isatty():
            resp = input("  Snapshot com mais de %.0f dias. Continuar? [s/N] " % args.max_age)
            if resp.strip().lower() not in ("s", "sim", "y"):
                return 1
        else:
            print("  aviso: snapshot com mais de %.0f dias; a comparacao pode estar velha"
                  % args.max_age)
    if dados.get("tipo") == "dry-run":
        print("  aviso: e' um dry-run; nada foi encerrado nele")
    cedo = cmux is not None and time.time() - cmux < RESTORE_EM_CURSO
    if cedo:
        print("  O cmux abriu ha %d s: o restore pode nao ter terminado. Rode de novo em uns"
              " 2 min." % (time.time() - cmux))
    if not dados.get("concluido", True):
        print("  aviso: o --apply deste snapshot nao chegou ao fim")
    if cmux is not None and cmux < ler(dados["gerado_em"]).timestamp():
        print("  O cmux nao foi reaberto desde este snapshot: a conferencia que vale e' a de"
              " depois do Cmd+Q.")

    r = comparar(dados, estado, armadas or {}, inicios, cmux)
    viva = [x for x in r["controle"] if x["viva"]]
    print("\n  dormindo       %d  (sem processo e desarmadas)" % len(r["dormindo"]))
    if r["controle"] and viva:
        print("  controle       %d  (rodando)" % len(r["controle"]))
    elif r["controle"]:
        print("  controle       %d  FALHA: a aba de controle nao subiu; veja se o shell dela "
              "mostra 'conflict'" % len(r["controle"]))
        _listar(r["controle"])
    if r["vivas"]:
        print("  rodando        %d  (fora do plano de dormir)" % len(r["vivas"]))
    if r["subiu_sozinha"]:
        print("  subiu sozinha  %d  FALHA: o desarme nao pegou; rode o hibernate de novo"
              % len(r["subiu_sozinha"]))
        _listar(r["subiu_sozinha"])
    if r["nao_dormiu"]:
        print("  nao dormiu     %d  FALHA: o processo e' anterior ao hibernate"
              % len(r["nao_dormiu"]))
        _listar(r["nao_dormiu"])
    if r["suspeita"]:
        print("  suspeita       %d  FALHA provavel: nasceu depois do restore, mas o hibernate"
              " nao a conferiu desarmada" % len(r["suspeita"]))
        _listar(r["suspeita"], lambda x: "  ·  processo desde %s" % _hora(x["hora"]))
    if r["acordada"]:
        print("  acordada       %d  (e ficou armada para o proximo fechamento)"
              % len(r["acordada"]))
        _listar(r["acordada"], lambda x: "  ·  acordada por voce as %s" % _hora(x["hora"]))
    if r["armada"]:
        print("  armada         %d  aviso: sem processo, mas sobe no proximo fechamento"
              % len(r["armada"]))
        _listar(r["armada"])
    if r["ausentes"]:
        print("  ausentes       %d  (aba nao existe mais)" % len(r["ausentes"]))
        _listar(r["ausentes"])
    if r["sem_transcript"]:
        print("  sem transcript %d  (nao restauraveis)" % len(r["sem_transcript"]))

    falha = bool(r["subiu_sozinha"] or r["nao_dormiu"] or r["suspeita"]
                 or (r["controle"] and not viva))
    problema = (falha or r["ausentes"] or r["armada"] or armadas is None or cedo)
    if not problema and not args.up and not args.rebuild:
        print("\n  Nada a corrigir.")
    if r["dormindo"] and not args.up:
        print("\n  Para retomar uma: wake.py --up <workspace|all>, ou o comando do INVENTARIO.md.")

    if args.up:
        alvos = filtrar_alvo(r["dormindo"] + r["armada"], args.up)
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

    return 1 if falha else 0


if __name__ == "__main__":
    raise SystemExit(main())
