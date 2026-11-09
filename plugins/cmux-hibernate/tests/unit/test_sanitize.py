"""As fixtures sao publicas: o ambiente do processo sai por lista de permissao, nao de bloqueio."""
import base64
import pathlib
import re
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = RAIZ / "tests" / "fixtures"
sys.path.insert(0, str(FIXTURES))
import sanitize  # noqa: E402

SURF = "DEADBEEF-0000-4ABC-8DEF-000000000001"
SESS = "feedface-0000-4abc-8def-000000000002"
ARGV_REAL = base64.b64encode("\0".join(
    ["/Users/fulano/.local/bin/claude", "--resume", SESS, "--dangerously-skip-permissions",
     "--model"]).encode()).decode()
CRU = ("4242 /Users/fulano/.local/bin/claude --settings {\"hooks\":{}} --resume %s "
       "--dangerously-skip-permissions CMUX_SOCKET_CAPABILITY=v9.SEGREDO-inventado "
       "CMUX_AGENT_LAUNCH_ARGV_B64=%s CMUX_AGENT_LAUNCH_KIND=claude "
       "CMUX_SURFACE_ID=%s CMUX_WORKSPACE_ID=11111111-2222-4333-8444-555555555555 "
       "TMPDIR=/var/folders/zz/xyz/T/ HOME=/Users/fulano XPC_SERVICE_NAME=application.x.123 "
       "PATH=/Users/fulano/bin:/usr/bin" % (SESS, ARGV_REAL, SURF))
PERMITIDAS = {"CMUX_SURFACE_ID", "CMUX_WORKSPACE_ID", "CMUX_AGENT_LAUNCH_KIND",
              "CMUX_AGENT_LAUNCH_ARGV_B64"}
_VAR = re.compile(r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)=")


class TestLinhaPs(unittest.TestCase):
    def setUp(self):
        self.mai = sanitize.Mapa(sanitize.uuid_maiusculo)
        self.mino = sanitize.Mapa(sanitize.uuid_minusculo)
        self.linha = sanitize.sanitizar_ps(CRU, self.mai, self.mino)

    def test_so_variaveis_permitidas(self):
        self.assertEqual(set(_VAR.findall(self.linha)) - PERMITIDAS, set())

    def test_nada_do_ambiente_real(self):
        for proibido in ("SEGREDO", "fulano", "/var/folders", "application.x", SURF, SESS,
                         "--settings", ARGV_REAL):
            self.assertNotIn(proibido, self.linha)

    def test_argv_b64_recodificado_com_os_valores_sinteticos(self):
        b64 = re.search(r"CMUX_AGENT_LAUNCH_ARGV_B64=(\S+)", self.linha).group(1)
        argv = base64.b64decode(b64).decode().split("\0")
        self.assertEqual(argv, ["/Users/dev/.local/bin/claude", "--resume", self.mino.de(SESS),
                                "--dangerously-skip-permissions"])

    def test_preserva_o_que_os_parsers_leem(self):
        self.assertTrue(self.linha.startswith("4242 /Users/dev/.local/bin/claude --resume "))
        self.assertIn("CMUX_SURFACE_ID=%s" % self.mai.de(SURF), self.linha)

    def test_daemon_e_titulo_viram_marcadores_sinteticos(self):
        cru = ("7 /Users/f/.local/bin/claude daemon run CMUX_SURFACE_ID=%s" % SURF)
        self.assertIn(" daemon run ", sanitize.sanitizar_ps(cru, self.mai, self.mino))
        cru = ("8 /Users/f/.local/bin/claude --resume Cliente X: contrato CMUX_SURFACE_ID=%s"
               % SURF)
        saida = sanitize.sanitizar_ps(cru, self.mai, self.mino)
        self.assertNotIn("Cliente", saida)
        self.assertIn("--resume titulo-sintetico", saida)


class TestFixturesVersionadas(unittest.TestCase):
    """Guarda permanente: o que esta no repositorio nao carrega ambiente real."""

    PADRAO = re.compile(r"CMUX_SOCKET_CAPABILITY|/var/folders/|XPC_SERVICE_NAME|"
                        r"SSH_AUTH_SOCK|TMPDIR=|HOME=|--settings")

    def test_nenhuma_fixture_tem_ambiente_real(self):
        for f in sorted(FIXTURES.glob("*")):
            if f.is_file() and f.suffix in (".txt", ".json"):
                achado = self.PADRAO.search(f.read_text(errors="ignore"))
                self.assertIsNone(achado, "%s: %s" % (f.name, achado and achado.group(0)))

    def test_argv_b64_das_fixtures_e_sintetico(self):
        texto = (FIXTURES / "ps-eww.txt").read_text()
        valores = re.findall(r"CMUX_AGENT_LAUNCH_ARGV_B64=(\S+)", texto)
        for b64 in valores:
            argv = base64.b64decode(b64).decode()
            self.assertTrue(argv.startswith("/Users/dev/.local/bin/claude"), argv[:40])
            self.assertEqual(argv.split("\0")[0], argv.split("\0")[0].strip())

    def test_ps_eww_so_tem_variaveis_permitidas(self):
        texto = (FIXTURES / "ps-eww.txt").read_text()
        self.assertEqual(set(_VAR.findall(texto)) - PERMITIDAS, set())


if __name__ == "__main__":
    unittest.main()
