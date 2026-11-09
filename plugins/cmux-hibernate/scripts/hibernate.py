#!/usr/bin/env python3
"""Hiberna as sessoes Claude Code do cmux: encerra as ociosas e confere que nao sobem.

O padrao e' dry-run: mostra o plano por aba e nao toca em nada. Com --apply, encerra
com SIGTERM o claude ocioso de cada aba-alvo (o que libera a memoria e, pelo hook
SessionEnd, tira a aba do restore do cmux), limpa o registro das abas armadas sem
processo e confere tudo no autosave que o cmux regrava. "Pode dar Cmd+Q" so' sai
quando todas as abas-alvo foram conferidas desarmadas.

Saida: 0 no caminho normal; 1 quando alguma aba-alvo nao foi conferida desarmada
(no dry-run, so' com --surface, quando a aba pedida nao seria); 2 em erro de leitura
do cmux ou de argumento; 3 quando so' falta a sessao que roda o comando sair com /exit.
"""
import argparse
import os
import sys
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib import cmux_state  # noqa: E402
from lib.autosave import VERSAO_MEDIDA, ler_autosave, ler_hooks  # noqa: E402
from lib.bindings import abas_que_casam  # noqa: E402
from lib.cmux_state import (  # noqa: E402
    STALE_DAYS,
    _ps_eww,
    claudes_sem_aba,
    detectar_duplicatas,
    ler_estado,
    inicios_de,
    parse_processos,
    so_principais,
    versao_do_cmux,
)
from lib.diff import ultimo_apply, ultimo_para_inventario  # noqa: E402
from lib.encerrar import ancestrais, ler_fresco, motivo_ocupada  # noqa: E402
from lib.inventario import completar_inventario  # noqa: E402
from lib.plano import (  # noqa: E402
    CONTROLE, DORMINDO, ENCERRAR, LIMPAR, PULAR, conferencia_final, executar, marcar_erro,
    para_snapshot, pendente, planejar)
from lib.snapshot import (  # noqa: E402
    BASE_ESTADO, aplicar_retencao, gravar, gravar_dry_run, serializar)

_VERBO = {ENCERRAR: "encerrar", LIMPAR: "limpar", DORMINDO: "dormindo", PULAR: "pular",
          CONTROLE: "controle"}


def _linha(p: dict) -> str:
    extra = p["motivo"] or ("esta aba, preservada" if p["acao"] == CONTROLE else "")
    return "    %-9s %s  %-40s %s" % (_VERBO[p["acao"]], p["sessao"][:8],
                                      (p["titulo"] or "")[:40], extra)


def _ocupada_agora(hooks):
    """Reconfere a ociosidade logo antes do SIGTERM, com o transcript relido do disco."""
    def ver(item):
        caminho = (item.get("_transcript") or {}).get("path")
        try:
            mtime = os.stat(caminho).st_mtime if caminho else None
        except OSError:
            mtime = None
        return motivo_ocupada(item["sessao"], [mtime, _mais_recente_do_projeto(caminho)],
                              ler_hooks() or hooks, time.time(), surface=item["surface"])
    return ver


_SESSOES_DE_ABA: set = set()


def _mais_recente_do_projeto(transcript: Optional[str]) -> Optional[float]:
    """mtime do .jsonl mais recente do projeto da sessao (o diretorio do transcript),
    fora os das sessoes que outra aba tem. Depois de um /clear a aba escreve num arquivo
    novo, que nenhuma aba conhece; o de uma aba irma do mesmo projeto nao conta."""
    if not transcript:
        return None
    proprio = Path(transcript)
    try:
        return max((p.stat().st_mtime for p in proprio.parent.glob("*.jsonl")
                    if p == proprio or p.stem not in _SESSOES_DE_ABA), default=None)
    except OSError:
        return None


def _herdados(base: Path, so_aba: Optional[str], estado) -> list:
    """Com --surface, as outras abas herdam o plano do ultimo --apply: senao o wake
    perderia a cobertura delas. Herdado nao e' alvo: nada e' feito nele agora."""
    if so_aba is None:
        return []
    anterior = ultimo_apply(base) or {}
    existem = {a.uuid for *_, a in estado.todas_abas()}
    return [dict(p, herdado=True) for p in anterior.get("plano") or []
            if p.get("surface") != so_aba and p.get("surface") in existem]


def main() -> int:
    ap = argparse.ArgumentParser(description="Hiberna sessoes Claude Code no cmux.")
    ap.add_argument("--apply", action="store_true",
                    help="encerra as sessoes ociosas e confere (padrao: so' mostra o plano)")
    escopo = ap.add_mutually_exclusive_group()
    escopo.add_argument("--all", action="store_true",
                        help="inclui a aba de onde o comando foi chamado")
    escopo.add_argument("--surface", metavar="ABA",
                        help="so' esta aba (uuid ou ref surface:N), mesmo que seja a de "
                             "onde o comando foi chamado")
    ap.add_argument("--stale-days", type=int, default=STALE_DAYS)
    ap.add_argument("--estado", type=Path, default=BASE_ESTADO, metavar="DIR",
                    help="diretorio dos snapshots (padrao: %(default)s)")
    args = ap.parse_args()

    inicio_comando = time.time()
    try:
        estado = ler_estado()
        _, paineis = ler_autosave()
    except RuntimeError as e:
        print("erro: %s" % e, file=sys.stderr)
        return 2
    hooks = ler_hooks()
    trazidas = completar_inventario(estado, paineis, ultimo_para_inventario(args.estado),
                                    raiz=cmux_state.RAIZ_PROJETOS)

    so_aba = None
    if args.surface is not None:
        achadas = abas_que_casam(estado, args.surface)
        if len(achadas) != 1:
            print("erro: %s abas casam com %r; --surface pede exatamente uma"
                  % ("nenhuma" if not achadas else len(achadas), args.surface), file=sys.stderr)
            return 2
        if not achadas[0].sessao:
            print("erro: a aba %s nao tem sessao Claude Code" % achadas[0].ref, file=sys.stderr)
            return 2
        so_aba = achadas[0].uuid

    controle = None if args.all else (os.environ.get("CMUX_SURFACE_ID") or "").upper() or None
    abas = [a for *_, a in estado.todas_abas() if a.sessao]
    saida_ps = so_principais(_ps_eww())
    duplicadas = detectar_duplicatas(parse_processos(saida_ps))
    sem_aba = claudes_sem_aba(saida_ps)
    _SESSOES_DE_ABA.clear()
    _SESSOES_DE_ABA.update(a.sessao for a in abas)
    plano = planejar(estado, controle, duplicadas, so_aba, ancestrais(), hooks,
                     projeto_mtime=_mais_recente_do_projeto)
    transcripts = {a.uuid: a.transcript for a in abas}
    inicios = inicios_de([p["pid"] for p in plano if p["pid"]])
    for p in plano:
        p["_transcript"] = transcripts.get(p["surface"])
        p["inicio"] = inicios.get(p["pid"]) if p["pid"] else None
    herdados = _herdados(args.estado, so_aba, estado)

    versao = versao_do_cmux()
    if versao and VERSAO_MEDIDA not in versao:
        print("aviso: %s; a mecanica do desarme foi medida no cmux %s e pode ter mudado"
              % (versao, VERSAO_MEDIDA), file=sys.stderr)

    print("Estado real: %d sessoes em %d workspaces, %d janelas" % (
        len(abas), sum(len(j.workspaces) for j in estado.janelas), len(estado.janelas)))
    print("  %d com processo, %d so' no autosave do cmux, %d dormindo desde o --apply anterior"
          % (sum(1 for a in abas if a.pid), trazidas["autosave"], trazidas["snapshot"]))
    estagnadas = [a for a in abas if a.estagnada]
    if estagnadas:
        print("\n  %d sem atividade ha mais de %d dias:" % (len(estagnadas), args.stale_days))
        for a in estagnadas:
            print("      %s  %s" % (a.sessao[:8], (a.titulo or "")[:58]))
    if duplicadas:
        print("\n  anomalia: %d sessoes aparecem em mais de uma aba; serao puladas"
              % len(duplicadas))

    print("\n  Plano:")
    for p in plano:
        print(_linha(p))
    _avisar_sem_aba(sem_aba)

    escopo_nome = "surface" if so_aba else ("all" if args.all else "padrao")
    controle_snap = None if so_aba is not None and so_aba == controle else controle
    conta = {a: sum(1 for p in plano if p["acao"] == a) for a in _VERBO}

    if not args.apply:
        dados = serializar(estado, controle_snap, args.stale_days, tipo="dry-run",
                           plano=_limpo(plano), escopo=escopo_nome)
        dados["sem_aba"] = sem_aba
        destino = gravar_dry_run(dados, args.estado)
        print("\n  Encerraria %d, limparia %d, pularia %d; %d ja dormem (dry-run)."
              % (conta[ENCERRAR], conta[LIMPAR], conta[PULAR], conta[DORMINDO]))
        print("  Use --apply para valer. Nada foi encerrado nem escrito no cmux.")
        print("\n  Inventario do dry-run (fora da retencao): %s" % destino)
        if so_aba is not None and any(pendente(p) for p in plano):
            print("  A aba pedida e' a desta sessao: o --apply nao a encerra. Saia dela com"
                  " /exit, que desarma a aba.")
            return 3
        if so_aba is not None and any(p["acao"] == PULAR for p in plano):
            print("  A aba pedida seria pulada e continuaria armada.", file=sys.stderr)
            return 1
        return 0

    dados = serializar(estado, controle_snap, args.stale_days, tipo="apply",
                       plano=_limpo(plano) + herdados, escopo=escopo_nome, versao_cmux=versao)
    dados["concluido"] = False
    dados["sem_aba"] = sem_aba
    destino = gravar(dados, args.estado)  # antes dos sinais: o plano ja fica registrado
    fora = []
    try:
        executar(plano, paineis, ocupada_fn=_ocupada_agora(hooks))
        fora = conferencia_final(plano, paineis, inicio_comando, controle, so_aba is None,
                                 _ps_eww, ler_fresco)
        dados["concluido"] = True
    except Exception as e:  # o que ja foi encerrado tem de chegar ao snapshot
        print("erro no --apply: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        marcar_erro(plano, "erro no --apply antes da conferencia: %s" % e)
    except BaseException:
        marcar_erro(plano, "--apply interrompido antes da conferencia")
        raise
    finally:
        dados["plano"] = _limpo(plano) + herdados
        gravar(dados, args.estado)
        aplicar_retencao(args.estado)

    alvos = [p for p in plano if p["acao"] != CONTROLE]
    pendentes = [p for p in alvos if pendente(p)]
    falhas = [p for p in alvos if not pendente(p) and not p["resultado"]["verificado"]]
    print("\n  Resultado, conferido no autosave do cmux e no ps:")
    for p in alvos:
        r = p["resultado"]
        rotulo = "PENDENTE" if pendente(p) else ("ok" if r["verificado"] else "FALHOU")
        print("    %-8s %s  %-40s %s" % (rotulo, p["sessao"][:8], (p["titulo"] or "")[:40],
                                          r["erro"] or _feito(p)))
    for f in fora:
        print("    FALHOU   %s" % f)
    print("\n  Desarmadas e conferidas: %d de %d abas-alvo" % (
        len(alvos) - len(falhas) - len(pendentes), len(alvos)))
    if any(p["acao"] == CONTROLE for p in plano):
        print("  Esta aba continua armada: e' a unica que sobe quando o cmux reabrir.")
    print("\n  Snapshot: %s" % destino)
    if falhas or fora:
        print("\n  Nao de Cmd+Q ainda: %d abas podem subir sozinhas ao reabrir."
              % (len(falhas) + len(fora)), file=sys.stderr)
        print("  Resolva as que FALHOU e rode de novo.", file=sys.stderr)
        return 1
    if pendentes:
        print("\n  Falta um passo: saia desta sessao com /exit. O /exit encerra o claude e o hook")
        print("  SessionEnd desarma a aba. Depois disso, pode dar Cmd+Q; espere uns 10 s antes")
        print("  de reabrir o cmux.")
        return 3
    if sem_aba:
        print("\n  Antes do Cmd+Q, veja o aviso acima: %s fora do plano." % _conta_sem_aba(sem_aba))
    print("\n  Pode dar Cmd+Q. Nao abra as abas encerradas antes disso: abrir rearma a aba.")
    print("  Depois do Cmd+Q, espere uns 10 s antes de reabrir o cmux.")
    return 0


def _conta_sem_aba(sem_aba: list) -> str:
    return "%d claude vivo%s no cmux sem CMUX_SURFACE_ID" % (
        len(sem_aba), "" if len(sem_aba) == 1 else "s")


def _avisar_sem_aba(sem_aba: list) -> None:
    """Quem roda no cmux sem a variavel nao entra no plano, mas cai no Cmd+Q."""
    if not sem_aba:
        return
    um = len(sem_aba) == 1
    print("\n  aviso: %s. O plugin nao %s ve nem desarma, mas %s no Cmd+Q:"
          % (_conta_sem_aba(sem_aba), "o" if um else "os", "ele cai" if um else "eles caem"))
    for c in sem_aba:
        if c["sessao"]:
            retomar = "retome depois com: claude --resume %s" % c["sessao"]
        else:
            retomar = "sessao desconhecida: anote o que ela fazia antes do Cmd+Q"
        print("    pid %s  %s  %s" % (c["pid"], c["cwd"] or "", retomar))


def _feito(p: dict) -> str:
    return {"sigterm": "encerrada", "sigterm+rpc": "encerrada; registro limpo pelo rpc",
            "rpc": "registro limpo pelo rpc"}.get(p["resultado"]["metodo"], "ja dormia")


def _limpo(plano):
    return [{k: v for k, v in p.items() if not k.startswith("_")} for p in para_snapshot(plano)]


if __name__ == "__main__":
    raise SystemExit(main())
