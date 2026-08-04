import json
import pathlib
import sys
import tempfile
import time
import unittest

RAIZ = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ / "scripts"))
from lib.cmux_state import (  # noqa: E402
    Aba,
    Estado,
    Janela,
    Pane,
    Workspace,
    cwd_do_transcript,
    localizar_transcript,
    marcar_estagnadas,
)


class TestTranscripts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = pathlib.Path(self.tmp.name)
        # dois slugs para o mesmo projeto — o cenario do symlink
        (self.raiz / "-Users-x-Documents-tech-projects-app").mkdir(parents=True)
        (self.raiz / "-Users-x-tech-projects-app").mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def _escrever(self, slug, sessao, cwd):
        p = self.raiz / slug / (sessao + ".jsonl")
        p.write_text(json.dumps({"cwd": cwd, "message": {"role": "user"}}) + "\n")
        return p

    def test_localiza_em_qualquer_slug(self):
        sessao = "11111111-2222-3333-4444-555555555555"
        self._escrever("-Users-x-Documents-tech-projects-app", sessao, "/Users/x/tech_projects/app")
        achado = localizar_transcript(sessao, self.raiz)
        self.assertIsNotNone(achado)
        self.assertTrue(achado.name.startswith(sessao))

    def test_cwd_vem_de_dentro_do_arquivo_nao_do_slug(self):
        """O nome do diretorio pode mentir apos um symlink; o conteudo, nao."""
        sessao = "66666666-7777-8888-9999-000000000000"
        p = self._escrever("-Users-x-Documents-tech-projects-app", sessao,
                           "/Users/x/tech_projects/app")
        self.assertEqual(cwd_do_transcript(p), "/Users/x/tech_projects/app")

    def test_transcript_ausente_retorna_none(self):
        self.assertIsNone(
            localizar_transcript("00000000-0000-0000-0000-000000000000", self.raiz))

    def test_marca_estagnada_por_mtime(self):
        agora = time.time()
        velha = Aba(uuid="A", ref="surface:1", tipo="terminal", titulo="velha",
                    sessao="s1", transcript={"mtime": agora - 10 * 86400})
        nova = Aba(uuid="B", ref="surface:2", tipo="terminal", titulo="nova",
                   sessao="s2", transcript={"mtime": agora - 3600})
        estado = Estado(janelas=[Janela(uuid="W", ref="window:1", workspaces=[
            Workspace(uuid="S", ref="workspace:1", nome="ws",
                      panes=[Pane(uuid="P", ref="pane:1", abas=[velha, nova])])])])
        marcar_estagnadas(estado, agora=agora, stale_days=7)
        self.assertTrue(velha.estagnada)
        self.assertFalse(nova.estagnada)


if __name__ == "__main__":
    unittest.main()
