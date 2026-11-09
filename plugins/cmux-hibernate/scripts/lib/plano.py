"""O plano do hibernate, aba a aba, e a execucao do --apply.

Acoes:
    encerrar  processo vivo e ocioso: SIGTERM no claude da aba
    limpar    armada no autosave sem processo: rpc surface.resume.clear
    dormindo  sem processo e nao armada: nada a fazer
    pular     ocupada, sessao em mais de uma aba, ou a sessao que roda este comando
    controle  a aba de onde o comando roda, preservada (nao e' alvo)

Nenhum resultado e' "verificado" sem o autosave regravado dizer que a aba nao sobe.
"""
import time
from typing import Callable, Dict, Iterable, List, Optional

from lib.autosave import Painel
from lib.carimbo import agora_utc
from lib.cmux_state import claudes_por_surface
from lib.encerrar import conferir, encerrar, limpar_registro, motivo_ocupada, processo_confere

ENCERRAR, LIMPAR, DORMINDO, PULAR, CONTROLE = "encerrar", "limpar", "dormindo", "pular", "controle"
PROPRIA = "e' a sessao que roda este comando: saia dela com /exit antes do Cmd+Q"


def planejar(estado, controle: Optional[str], duplicadas: Optional[Iterable[str]] = None,
             so_aba: Optional[str] = None, protegidos: Iterable[str] = (),
             hooks: Optional[Dict[str, dict]] = None, agora: Optional[float] = None,
             projeto_mtime: Optional[Callable[[Optional[str]], Optional[float]]] = None
             ) -> List[dict]:
    """Uma entrada por aba com sessao. Com so_aba (uuid), so' aquela aba, mesmo que seja a
    de controle: e' o que deixa uma sessao hibernar a propria aba, como no revezamento."""
    proibidas, protegidos = set(duplicadas or []), set(protegidos)
    hooks, agora = hooks or {}, time.time() if agora is None else agora
    plano = []
    for janela, ws, _pane, aba in estado.todas_abas():
        if not aba.sessao or (so_aba is not None and aba.uuid != so_aba):
            continue
        item = {"surface": aba.uuid, "janela": janela.uuid, "workspace": ws.uuid,
                "ws_nome": ws.nome, "sessao": aba.sessao, "cwd": aba.cwd, "titulo": aba.titulo,
                "fonte": aba.fonte, "pid": aba.pid, "armada": aba.armada, "acao": None,
                "motivo": None, "resultado": None}
        t = aba.transcript or {}
        mtimes = [t.get("mtime"), projeto_mtime(t.get("path")) if projeto_mtime else None]
        ocupada = motivo_ocupada(aba.sessao, mtimes, hooks, agora, surface=aba.uuid)
        if aba.sessao in proibidas:
            item["acao"], item["motivo"] = PULAR, "sessao em mais de uma aba (anomalia)"
        elif so_aba is None and aba.uuid == controle:
            item["acao"] = CONTROLE
        elif aba.pid and aba.pid in protegidos:
            item["acao"], item["motivo"] = PULAR, PROPRIA
        elif aba.pid and ocupada:
            item["acao"], item["motivo"] = PULAR, "ocupada: " + ocupada
        elif aba.pid:
            item["acao"] = ENCERRAR
        elif aba.armada:
            item["acao"], item["motivo"] = LIMPAR, "armada (%s) sem processo" % aba.armada
        else:
            item["acao"] = DORMINDO
        plano.append(item)
    return plano


def para_snapshot(plano: List[dict]) -> List[dict]:
    """O pid e o instante em que o processo nasceu nao vao ao snapshot: sao estado do
    momento e envelheceriam em silencio."""
    return [{k: v for k, v in p.items() if k not in ("pid", "inicio")} for p in plano]


def pendente(item: dict) -> bool:
    """A sessao que roda o comando: nao e' falha, falta o /exit dela."""
    return item["acao"] == PULAR and item.get("motivo") == PROPRIA


def _resultado(item: dict, metodo: Optional[str], erro: Optional[str]) -> None:
    item["resultado"] = {"metodo": metodo, "verificado": erro is None, "quando": agora_utc(),
                         "erro": erro}


def marcar_erro(plano: List[dict], motivo: str) -> None:
    """Depois de uma excecao no --apply: todo alvo sem resultado fica nao verificado."""
    for item in plano:
        if item["acao"] != CONTROLE and item["resultado"] is None:
            _resultado(item, None, motivo)


def _painel(item: dict, paineis: Dict[str, Painel]) -> Painel:
    p = paineis.get(item["surface"].upper())
    return Painel(surface=item["surface"], janela=p.janela if p else item["janela"],
                  workspace=p.workspace if p else item["workspace"],
                  sessao=(p.sessao if p and p.sessao else item["sessao"]), cwd=item["cwd"],
                  armado=item["armada"])


def executar(plano: List[dict], paineis: Dict[str, Painel], confere=processo_confere,
             encerrar_fn=encerrar, limpar_fn=limpar_registro, conferir_fn=conferir,
             ocupada_fn: Optional[Callable[[dict], Optional[str]]] = None,
             agora: Callable[[], float] = time.time) -> None:
    """Executa o plano e grava `resultado` em cada alvo. A aba de controle fica com None."""
    inicio = agora()
    sinalizar = []
    for item in plano:
        if item["acao"] != ENCERRAR:
            continue
        motivo = ocupada_fn(item) if ocupada_fn else None
        if motivo:
            item["acao"], item["motivo"] = PULAR, "ocupada: " + motivo
        elif item.get("inicio") is None:
            _resultado(item, None, "nao li quando o processo %s nasceu; nenhum sinal enviado"
                       % item["pid"])
        elif not confere(item["pid"], item["surface"], item["inicio"]):
            _resultado(item, None, "o processo %s mudou desde a leitura; nenhum sinal enviado"
                       % item["pid"])
        else:
            sinalizar.append(item)
    restantes = encerrar_fn([i["pid"] for i in sinalizar])
    sairam = []
    for item in sinalizar:
        if item["pid"] in restantes:
            _resultado(item, "sigterm", "o claude nao saiu em 10 s do SIGTERM; SIGKILL nao e' "
                                        "usado, encerre com /exit")
        else:
            sairam.append(item)
    limpar = [i for i in plano if i["acao"] == LIMPAR]
    falha_rpc = {}

    def pedir_limpeza(item):
        try:
            limpar_fn(_painel(item, paineis))
        except Exception as e:  # cmux fora do PATH, timeout: quem julga e' a conferencia
            falha_rpc[item["surface"]] = "rpc falhou (%s)" % e

    def erro(item, res):
        motivo = res.get(item["surface"].upper())
        extra = falha_rpc.get(item["surface"])
        return "%s; %s" % (motivo, extra) if motivo and extra else motivo

    for item in limpar:
        pedir_limpeza(item)
    iniciais = set(paineis)
    res = conferir_fn([i["surface"] for i in sairam + limpar], depois_de=inicio,
                      iniciais=iniciais)
    for item in limpar:
        _resultado(item, "rpc", erro(item, res))
    reserva = [i for i in sairam if res.get(i["surface"].upper())]
    for item in sairam:
        if item not in reserva:
            _resultado(item, "sigterm", None)
    if reserva:
        marco = agora()
        for item in reserva:
            pedir_limpeza(item)
        res2 = conferir_fn([i["surface"] for i in reserva], depois_de=marco, iniciais=iniciais)
        for item in reserva:
            _resultado(item, "sigterm+rpc", erro(item, res2))
    for item in plano:
        if item["acao"] == PULAR:
            _resultado(item, None, item["motivo"])
    # DORMINDO fica sem resultado: quem o da' e' a conferencia_final, no autosave relido


def conferencia_final(plano: List[dict], iniciais: Iterable[str], depois_de: float,
                      controle: Optional[str], escopo_total: bool, ps_fn, ler_fresco
                      ) -> List[str]:
    """A ultima palavra antes do "Pode dar Cmd+Q", sobre o autosave relido e um ps novo.

    Cada alvo (inclusive o que ja dormia) so' fica verificado se o autosave regravado
    depois de `depois_de` nao o tem armado, se o painel nao sumiu, e se nao resta nenhum
    claude na aba. Com `escopo_total` (sem --surface), qualquer painel armado ou claude
    vivo fora da aba de controle e dos alvos tambem impede o fechamento: e' a lista
    devolvida."""
    excluir = {(controle or "").upper()} | {i["surface"].upper() for i in plano if pendente(i)}
    alvos = [i for i in plano if i["acao"] != CONTROLE and not pendente(i)]
    vivos = {s.upper(): pids for s, pids in claudes_por_surface(ps_fn()).items()}
    paineis, erro_leitura = ler_fresco(depois_de)
    iniciais = {s.upper() for s in iniciais}
    for item in alvos:
        s = item["surface"].upper()
        motivo = None
        if s in vivos:
            motivo = "ainda ha claude na aba (pid %s)" % ", ".join(vivos[s])
        elif paineis is None:
            motivo = erro_leitura
        elif not paineis:
            motivo = "o autosave nao tem paineis de terminal"
        elif s not in paineis and s in iniciais:
            motivo = "o painel sumiu do autosave"
        elif s in paineis and paineis[s].armado:
            motivo = "continua armada (%s)" % paineis[s].armado
        r = item["resultado"]
        if motivo:
            antes = r["erro"] if r and r["erro"] else None
            _resultado(item, r["metodo"] if r else None,
                       "%s; %s" % (antes, motivo) if antes and antes != motivo else motivo)
        elif r is None:
            _resultado(item, None, None)
    if not escopo_total:
        return []
    conhecidas = excluir | {i["surface"].upper() for i in alvos}
    fora = ["claude vivo na aba %s (pid %s), fora do plano" % (s, ", ".join(p))
            for s, p in sorted(vivos.items()) if s not in conhecidas]
    if paineis is None:
        fora.append(erro_leitura)
    else:
        fora += ["aba %s armada (%s), fora do plano" % (s, p.armado)
                 for s, p in sorted(paineis.items()) if p.armado and s not in conhecidas]
    return fora
