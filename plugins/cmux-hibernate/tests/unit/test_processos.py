import pathlib
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import (  # noqa: E402
    Estado,
    aplicar_processos,
    detectar_duplicatas,
    parse_processos,
    parse_tree,
)

FIX_TREE = (RAIZ / "tests/fixtures/tree.txt").read_text()
FIX_PS = (RAIZ / "tests/fixtures/ps-eww.txt").read_text()


class TestProcessos(unittest.TestCase):
    def test_extrai_sessao_e_surface(self):
        mapa = parse_processos(FIX_PS)
        self.assertGreater(len(mapa), 0)
        for surface, info in mapa.items():
            self.assertRegex(surface, r"^[0-9A-F-]{36}$")
            self.assertRegex(info["sessao"], r"^[0-9a-f-]{36}$")

    def test_aplica_no_estado_e_marca_fonte(self):
        estado = Estado(janelas=parse_tree(FIX_TREE))
        aplicar_processos(estado, parse_processos(FIX_PS), cwds={})
        com_sessao = [a for *_, a in estado.todas_abas() if a.sessao]
        self.assertGreater(len(com_sessao), 0)
        self.assertTrue(all(a.fonte == "processo" for a in com_sessao))

    def test_regressao_binding_desatualizado(self):
        """Binding diz sessao A; processo roda sessao B. Deve vencer B.

        Foi esta falha que escondeu 7 conversas no ciclo de 27-28/07/2026.
        """
        estado = Estado(janelas=parse_tree(FIX_TREE))
        alvo = next(a for *_, a in estado.todas_abas() if a.tipo == "terminal")
        alvo.sessao, alvo.fonte = "aaaaaaaa-1111-2222-3333-444444444444", "binding"
        mapa = {alvo.uuid: {"sessao": "bbbbbbbb-5555-6666-7777-888888888888", "pid": "999"}}
        aplicar_processos(estado, mapa, cwds={"999": "/tmp/projeto"})
        self.assertEqual(alvo.sessao, "bbbbbbbb-5555-6666-7777-888888888888")
        self.assertEqual(alvo.fonte, "processo")
        self.assertEqual(alvo.cwd, "/tmp/projeto")

    def test_ignora_daemon_e_bg(self):
        linhas = [
            "111 /Users/x/.local/bin/claude daemon run --json-path /x "
            "CMUX_SURFACE_ID=AAAAAAAA-1111-2222-3333-444444444444",
            "222 /Users/x/.local/bin/claude --resume bbbbbbbb-5555-6666-7777-888888888888 "
            "CMUX_SURFACE_ID=CCCCCCCC-1111-2222-3333-444444444444",
        ]
        mapa = parse_processos("\n".join(linhas))
        self.assertEqual(len(mapa), 1)
        self.assertIn("CCCCCCCC-1111-2222-3333-444444444444", mapa)

    def test_detecta_sessao_duplicada(self):
        """Mesma sessao em duas abas e' anomalia: nao desarmar nem subir."""
        linhas = [
            "1 /Users/x/.local/bin/claude --resume dddddddd-1111-2222-3333-444444444444 "
            "CMUX_SURFACE_ID=AAAAAAAA-1111-2222-3333-444444444444",
            "2 /Users/x/.local/bin/claude --resume dddddddd-1111-2222-3333-444444444444 "
            "CMUX_SURFACE_ID=BBBBBBBB-1111-2222-3333-444444444444",
        ]
        mapa = parse_processos("\n".join(linhas))
        self.assertEqual(detectar_duplicatas(mapa), ["dddddddd-1111-2222-3333-444444444444"])


if __name__ == "__main__":
    unittest.main()
