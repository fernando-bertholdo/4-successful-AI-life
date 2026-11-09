import pathlib
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from fuso import FusoFixo  # noqa: E402
from lib.cmux_state import (  # noqa: E402
    Estado,
    _inicios_de_ps,
    _inicio_do_cmux_de_ps,
    aplicar_processos,
    claudes_sem_aba,
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



class TestPrincipal(unittest.TestCase):
    """Varios claude na mesma aba: o principal e' o que nao descende de outro claude."""

    A = "AAAAAAAA-1111-2222-3333-444444444444"
    LINHAS = "\n".join([
        "10 /Users/x/.local/bin/claude --resume aaaaaaaa-1111-2222-3333-444444444444 "
        "CMUX_SURFACE_ID=%s" % A,
        "30 /Users/x/.local/bin/claude -p resumo CMUX_SURFACE_ID=%s" % A,
        "40 /Users/x/.local/bin/claude --resume bbbbbbbb-1111-2222-3333-444444444444 "
        "CMUX_SURFACE_ID=BBBBBBBB-1111-2222-3333-444444444444"])
    PAIS = {"30": "20", "20": "10", "10": "5", "5": "1", "40": "6", "6": "1"}

    def test_lista_todos_os_claude_por_aba(self):
        from lib.cmux_state import claudes_por_surface
        self.assertEqual(claudes_por_surface(self.LINHAS)[self.A], ["10", "30"])

    def test_filho_aninhado_sai_e_o_principal_fica(self):
        from lib.cmux_state import so_principais
        saida = so_principais(self.LINHAS, ppid=self.PAIS.get)
        self.assertEqual([l.split()[0] for l in saida.splitlines()], ["10", "40"])
        self.assertEqual(parse_processos(saida)[self.A]["pid"], "10")

    def test_sem_como_ler_os_pais_fica_o_primeiro(self):
        from lib.cmux_state import so_principais
        saida = so_principais(self.LINHAS, ppid=lambda p: None)
        self.assertEqual([l.split()[0] for l in saida.splitlines()], ["10", "40"])


class TestInicios(FusoFixo, unittest.TestCase):
    """`ps -o lstart` sai na hora local do host: o fuso fixo confere a conta."""

    FUSO = "America/Sao_Paulo"

    def test_le_pid_e_lstart(self):
        saida = "  101 Sat Oct 31 02:37:54 2026\n 2002 Sat Oct 31 02:52:00 2026\n"
        self.assertEqual(_inicios_de_ps(saida), {"101": 1793425074.0, "2002": 1793425920.0})

    def test_ignora_linha_estranha(self):
        self.assertEqual(_inicios_de_ps("lixo\n  7 Sat Foo 99\n"), {})

    def test_inicio_do_cmux_e_o_do_app(self):
        saida = ("  500 Sat Oct 31 01:00:00 2026     /usr/bin/zsh\n"
                 "89502 Sat Oct 31 02:37:52 2026     /Applications/cmux.app/Contents/MacOS/cmux\n"
                 "  600 Sat Oct 31 02:38:00 2026     /Applications/cmux.app/Contents/Resources"
                 "/bin/cmux tree\n")
        self.assertEqual(_inicio_do_cmux_de_ps(saida), 1793425072.0)
        self.assertIsNone(_inicio_do_cmux_de_ps("  500 Sat Oct 31 01:00:00 2026  /bin/zsh\n"))


if __name__ == "__main__":
    unittest.main()


class TestRetomadaPorTitulo(unittest.TestCase):
    """O cmux retoma por titulo quando a sessao foi renomeada, e ai o id nao
    aparece no argv. Sem isso, a aba fica invisivel ao snapshot."""

    LINHA = ("3149 /Users/x/.local/bin/claude --dangerously-skip-permissions "
             "--resume meu-titulo: com espacos e dois pontos "
             "CMUX_SURFACE_ID=3A237047-5F4A-4A93-8805-FCB87453FE44")

    def test_parse_processos_nao_reconhece(self):
        self.assertEqual(parse_processos(self.LINHA), {})

    def test_surfaces_com_processo_reconhece(self):
        from lib.cmux_state import surfaces_com_processo
        vivos = surfaces_com_processo(self.LINHA)
        self.assertEqual(vivos, {"3A237047-5F4A-4A93-8805-FCB87453FE44": "3149"})

    def test_surfaces_com_processo_ignora_daemon(self):
        from lib.cmux_state import surfaces_com_processo
        linha = ("1 /Users/x/.local/bin/claude daemon run "
                 "CMUX_SURFACE_ID=AAAAAAAA-1111-2222-3333-444444444444")
        self.assertEqual(surfaces_com_processo(linha), {})


class TestClaudeSemAba(unittest.TestCase):
    """Claude aberto no cmux sem CMUX_SURFACE_ID: o plugin nao o ve, mas ele cai no Cmd+Q.

    Caso real de 09/11/2026: uma sessao aberta enquanto o socket recusava todo cliente
    ficou sem a variavel e sumiria no quit sem aparecer no inventario.
    """
    SEM_ABA = ("6001 /Users/x/.local/bin/claude --dangerously-skip-permissions "
               "__CFBundleIdentifier=com.cmuxterm.app TERM_PROGRAM=ghostty")
    COM_ABA = ("6002 /Users/x/.local/bin/claude --resume bbbbbbbb-5555-6666-7777-888888888888 "
               "__CFBundleIdentifier=com.cmuxterm.app "
               "CMUX_SURFACE_ID=CCCCCCCC-1111-2222-3333-444444444444")
    FORA_DO_CMUX = ("6003 /Users/x/.local/bin/claude --dangerously-skip-permissions "
                    "__CFBundleIdentifier=com.apple.Terminal TERM_PROGRAM=Apple_Terminal")
    DAEMON = ("6004 /Users/x/.local/bin/claude daemon run --json-path /x "
              "__CFBundleIdentifier=com.cmuxterm.app")
    COM_ID = ("6005 /Users/x/.local/bin/claude --session-id "
              "dddddddd-1111-2222-3333-444444444444 __CFBundleIdentifier=com.cmuxterm.app")

    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sessoes = pathlib.Path(self.tmp.name)

    def test_acha_so_o_do_cmux_sem_aba(self):
        saida = "\n".join([self.SEM_ABA, self.COM_ABA, self.FORA_DO_CMUX, self.DAEMON])
        achados = claudes_sem_aba(saida, raiz_sessoes=self.sessoes)
        self.assertEqual([a["pid"] for a in achados], ["6001"])
        self.assertIsNone(achados[0]["sessao"])

    def test_sessao_vem_do_argv(self):
        achados = claudes_sem_aba(self.COM_ID, raiz_sessoes=self.sessoes)
        self.assertEqual(achados[0]["sessao"], "dddddddd-1111-2222-3333-444444444444")

    def test_sessao_e_cwd_vem_do_registro_do_claude_por_pid(self):
        (self.sessoes / "6001.json").write_text(
            '{"pid": 6001, "sessionId": "eeeeeeee-1111-2222-3333-444444444444", '
            '"cwd": "/Users/x/projeto"}')
        achado = claudes_sem_aba(self.SEM_ABA, raiz_sessoes=self.sessoes)[0]
        self.assertEqual(achado["sessao"], "eeeeeeee-1111-2222-3333-444444444444")
        self.assertEqual(achado["cwd"], "/Users/x/projeto")

    def test_registro_de_outro_pid_nao_vale(self):
        (self.sessoes / "6001.json").write_text(
            '{"pid": 9999, "sessionId": "eeeeeeee-1111-2222-3333-444444444444"}')
        self.assertIsNone(claudes_sem_aba(self.SEM_ABA, raiz_sessoes=self.sessoes)[0]["sessao"])

    def test_registro_ilegivel_nao_quebra(self):
        (self.sessoes / "6001.json").write_text("{nao e json")
        self.assertIsNone(claudes_sem_aba(self.SEM_ABA, raiz_sessoes=self.sessoes)[0]["sessao"])
