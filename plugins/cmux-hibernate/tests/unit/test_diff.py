import calendar
import json
import pathlib
import sys
import tempfile
import time
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fuso import FusoFixo  # noqa: E402
from lib.cmux_state import Aba, Estado, Janela, Pane, Workspace  # noqa: E402
from lib.diff import (  # noqa: E402
    carregar_snapshot, comparar, idade_em_dias, ultimo_apply, ultimo_para_inventario)

SNAP = {
    "gerado_em": "2026-08-04T14:22:31",
    "janelas": [{"uuid": "W", "ref": "window:1", "workspaces": [{
        "uuid": "S", "ref": "workspace:1", "nome": "proj", "panes": [{
            "uuid": "P", "ref": "pane:1", "abas": [
                {"uuid": "A1", "sessao": "1111", "titulo": "viva", "cwd": "/tmp/a",
                 "tipo": "terminal", "transcript": {"path": "/t1.jsonl"}},
                {"uuid": "A2", "sessao": "2222", "titulo": "dormindo", "cwd": "/tmp/b",
                 "tipo": "terminal", "transcript": {"path": "/t2.jsonl"}},
                {"uuid": "A3", "sessao": "3333", "titulo": "sumiu", "cwd": "/tmp/c",
                 "tipo": "terminal", "transcript": {"path": "/t3.jsonl"}},
            ]}]}]}]}


def estado_atual():
    viva = Aba(uuid="A1", ref="surface:1", tipo="terminal", titulo="viva",
               sessao="1111", fonte="processo")
    dormindo = Aba(uuid="A2", ref="surface:2", tipo="terminal", titulo="dormindo")
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="proj",
                  panes=[Pane(uuid="P", ref="pane:1", abas=[viva, dormindo])])])])


class TestDiff(unittest.TestCase):
    def setUp(self):
        self.r = comparar(SNAP, estado_atual())

    def test_identifica_viva(self):
        self.assertEqual([x["sessao"] for x in self.r["vivas"]], ["1111"])

    def test_identifica_dormindo(self):
        """Aba existe na estrutura mas nenhum processo roda a sessao."""
        self.assertEqual([x["sessao"] for x in self.r["dormindo"]], ["2222"])

    def test_identifica_ausente(self):
        """Aba do snapshot que nao existe mais na estrutura atual."""
        self.assertEqual([x["sessao"] for x in self.r["ausentes"]], ["3333"])

    def test_chave_e_sessao_nao_titulo(self):
        """Titulos mentem: uma aba pode exibir o nome de outro projeto."""
        snap = {"janelas": [{"uuid": "W", "ref": "w", "workspaces": [{
            "uuid": "S", "ref": "s", "nome": "n", "panes": [{"uuid": "P", "ref": "p", "abas": [
                {"uuid": "A1", "sessao": "1111", "titulo": "TITULO COMPLETAMENTE DIFERENTE",
                 "cwd": "/tmp/a", "tipo": "terminal",
                 "transcript": {"path": "/t.jsonl"}}]}]}]}]}
        self.assertEqual(len(comparar(snap, estado_atual())["vivas"]), 1)


class TestIdade(FusoFixo, unittest.TestCase):
    FUSO = "America/Sao_Paulo"

    def test_idade_em_dias_formato_antigo(self):
        """Snapshot gravado ate' a 0.1.0: hora local do host, sem zona (14:22:31 em -03 = 17:22:31Z)."""
        base = calendar.timegm((2026, 8, 4, 17, 22, 31))
        self.assertAlmostEqual(idade_em_dias(SNAP, base + 2 * 86400), 2.0, places=6)

    def test_idade_em_dias_formato_utc(self):
        snap = dict(SNAP, gerado_em="2026-10-03T22:30:00Z")
        base = calendar.timegm((2026, 10, 3, 22, 30, 0))
        self.assertAlmostEqual(idade_em_dias(snap, base + 2 * 86400), 2.0, places=6)


class TestCarregarSnapshot(FusoFixo, unittest.TestCase):
    def _grava(self, base, nome, gerado_em, tipo="apply"):
        d = base / nome
        d.mkdir()
        dados = {"gerado_em": gerado_em}
        if tipo:
            dados["tipo"] = tipo
        (d / "snapshot.json").write_text(json.dumps(dados))
        return d

    def test_le_snapshot_gravado_antes_do_conserto(self):
        """Ate' a 0.2.0 o snapshot nao dizia o tipo: so' entra pedido pelo nome."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            d = self._grava(base, "2026-08-04T14-22-31", "2026-08-04T14:22:31", tipo=None)
            dados, origem = carregar_snapshot(base, d)
            self.assertEqual(origem.name, "2026-08-04T14-22-31")
            self.assertGreater(idade_em_dias(dados, time.time()), 0)
            with self.assertRaises(RuntimeError) as ctx:
                carregar_snapshot(base)
            self.assertIn("--apply", str(ctx.exception))

    def test_escolhe_o_ultimo_apply_e_ignora_dry_run(self):
        """F5: o mais recente pode ser um dry-run de desenvolvimento de outra aba."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            self._grava(base, "2026-10-31T05-36-55Z", "2026-10-31T05:36:55Z")
            self._grava(base, "2026-10-31T06-00-00Z", "2026-10-31T06:00:00Z", tipo="dry-run")
            self._grava(base, "ultimo-dry-run", "2026-10-31T07:00:00Z", tipo="dry-run")
            _, origem = carregar_snapshot(base)
            self.assertEqual(origem.name, "2026-10-31T05-36-55Z")
            self.assertEqual(ultimo_apply(base)["gerado_em"], "2026-10-31T05:36:55Z")

    def test_inventario_aceita_o_snapshot_sem_tipo_mas_nao_o_dry_run(self):
        """Quem ja dormia antes da 0.3.0 so' esta no snapshot da 0.2.0, que nao diz o tipo."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            self._grava(base, "2026-10-31T05-36-55Z", "2026-10-31T05:36:55Z", tipo=None)
            self._grava(base, "2026-10-31T06-00-00Z", "2026-10-31T06:00:00Z", tipo="dry-run")
            self._grava(base, "ultimo-dry-run", "2026-10-31T07:00:00Z", tipo="dry-run")
            self.assertEqual(ultimo_para_inventario(base)["gerado_em"], "2026-10-31T05:36:55Z")
            self._grava(base, "2026-10-31T05-40-00Z", "2026-10-31T05:40:00Z")
            self.assertEqual(ultimo_para_inventario(base)["gerado_em"], "2026-10-31T05:40:00Z")

    def test_ultimo_apply_sem_nada_e_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(ultimo_apply(pathlib.Path(tmp) / "nao-existe"))

    def test_escolhe_o_mais_recente_entre_os_dois_formatos(self):
        """A ordem e' a do instante, nao a do nome: hora local e UTC nao se comparam como texto."""
        with tempfile.TemporaryDirectory() as tmp:
            base = pathlib.Path(tmp)
            # Em Toquio (UTC+9), 07:00 local de 04/10 e' 22:00Z de 03/10: uma hora antes do novo.
            self._grava(base, "2026-10-04T07-00-00", "2026-10-04T07:00:00")
            self._grava(base, "2026-10-03T23-00-00Z", "2026-10-03T23:00:00Z")
            _, origem = carregar_snapshot(base)
            self.assertEqual(origem.name, "2026-10-03T23-00-00Z")


# --- comparacao contra o plano do --apply (0.3.0) -------------------------------------
CMUX = calendar.timegm((2026, 10, 31, 5, 37, 52))       # o cmux reabriu as 02:37:52 BRT
GERADO = "2026-10-31T05:36:55Z"


def snap_com_plano():
    abas, plano = [], []
    for n, acao in enumerate(["controle", "encerrar", "encerrar", "encerrar", "limpar",
                              "dormindo", "encerrar", "pular", "encerrar"], start=1):
        u = "U%d" % n
        abas.append({"uuid": u, "sessao": "s%d" % n, "titulo": "t%d" % n, "cwd": "/tmp",
                     "tipo": "terminal", "transcript": {"path": "/t%d.jsonl" % n}})
        plano.append({"surface": u, "sessao": "s%d" % n, "acao": acao})
    return {"gerado_em": GERADO, "tipo": "apply", "aba_de_controle": "U1", "plano": plano,
            "janelas": [{"uuid": "W", "ref": "window:1", "workspaces": [{
                "uuid": "S", "ref": "workspace:1", "nome": "proj", "panes": [{
                    "uuid": "P", "ref": "pane:1", "abas": abas}]}]}]}


def estado_reaberto():
    """U1 controle viva; U2 subiu 2 s depois do cmux; U3 acordada as 02:52 BRT; U4 dorme;
    U5 dorme mas segue armada; U6 dorme; U7 com processo anterior ao snapshot; U8 pulada e
    viva; U9 sumiu."""
    pids = {"U1": "1", "U2": "2", "U3": "3", "U7": "7", "U8": "8"}
    abas = [Aba(uuid="U%d" % n, ref="surface:%d" % n, tipo="terminal", titulo="t%d" % n,
                sessao="s%d" % n if "U%d" % n in pids else None,
                fonte="processo" if "U%d" % n in pids else None, pid=pids.get("U%d" % n))
            for n in range(1, 9)]
    return Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
        Workspace(uuid="S", ref="workspace:1", nome="proj",
                  panes=[Pane(uuid="P", ref="pane:1", abas=abas)])])])


INICIOS = {"1": CMUX + 3, "2": CMUX + 2, "3": calendar.timegm((2026, 10, 31, 5, 52, 0)),
           "7": calendar.timegm((2026, 10, 31, 5, 0, 0)), "8": CMUX + 4}


class TestCompararComPlano(unittest.TestCase):
    def setUp(self):
        self.r = comparar(snap_com_plano(), estado_reaberto(), armadas={"U5": "agent"},
                          inicios=INICIOS, inicio_cmux=CMUX)

    def sessoes(self, chave):
        return [x["sessao"] for x in self.r[chave]]

    def test_subiu_sozinha_e_falha(self):
        """O caso de 31/10: planejada para dormir, processo nascido junto com o cmux."""
        self.assertEqual(self.sessoes("subiu_sozinha"), ["s2"])

    def test_acordada_pelo_usuario_traz_a_hora(self):
        self.assertEqual(self.sessoes("acordada"), ["s3"])
        self.assertEqual(self.r["acordada"][0]["hora"], INICIOS["3"])

    def test_dormindo_armada_e_controle(self):
        self.assertEqual(self.sessoes("dormindo"), ["s4", "s6"])
        self.assertEqual(self.sessoes("armada"), ["s5"])
        self.assertEqual(self.sessoes("controle"), ["s1"])

    def test_processo_anterior_ao_snapshot_nao_dormiu(self):
        self.assertEqual(self.sessoes("nao_dormiu"), ["s7"])

    def test_pulada_viva_e_rodando_sem_falha(self):
        self.assertEqual(self.sessoes("vivas"), ["s8"])

    def test_ausente(self):
        self.assertEqual(self.sessoes("ausentes"), ["s9"])

    def test_processo_sem_id_no_argv_tambem_conta(self):
        e = estado_reaberto()
        e.processos = {"U4": "4"}
        r = comparar(snap_com_plano(), e, armadas={}, inicios=dict(INICIOS, **{"4": CMUX + 1}),
                     inicio_cmux=CMUX)
        self.assertIn("s4", [x["sessao"] for x in r["subiu_sozinha"]])

    def test_acordada_sem_conferencia_no_hibernate_e_suspeita(self):
        """Item 4: o ambiente nao distingue o restore do claude digitado; o plano sim."""
        snap = snap_com_plano()
        for p in snap["plano"]:
            if p["surface"] == "U3":
                p["resultado"] = {"verificado": False, "erro": "continua armada (agent)"}
        r = comparar(snap, estado_reaberto(), armadas={}, inicios=INICIOS, inicio_cmux=CMUX)
        self.assertEqual([x["sessao"] for x in r["suspeita"]], ["s3"])
        self.assertEqual(r["acordada"], [])

    def test_sem_inicio_do_cmux_conta_como_subiu_sozinha(self):
        r = comparar(snap_com_plano(), estado_reaberto(), armadas={}, inicios={},
                     inicio_cmux=None)
        self.assertEqual([x["sessao"] for x in r["subiu_sozinha"]], ["s2", "s3", "s7"])


if __name__ == "__main__":
    unittest.main()
