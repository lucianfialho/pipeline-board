import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import build
import trace as gravador

# o módulo `trace` da biblioteca padrão não pode ter ganhado do nosso
assert pathlib.Path(gravador.__file__).parent == RAIZ / "scripts"


def reg(nome, seg, codigo=0, grupo="G", execucao="r1", ordem=0):
    return {"run": execucao, "group": grupo, "name": nome, "start": f"2026-01-01T00:00:{ordem:02d}", "seconds": seg, "exit": codigo}


class Gravar(unittest.TestCase):
    def roda(self, pasta, *comando, extras=()):
        arq = pathlib.Path(pasta) / "t.jsonl"
        r = subprocess.run([sys.executable, str(RAIZ / "scripts" / "trace.py"), "run", "passo", "--trace", str(arq), *extras, "--", *comando], capture_output=True, text=True)
        return r, arq

    def test_repassa_saida_e_codigo_sem_gravar_argumentos(self):
        with tempfile.TemporaryDirectory() as d:
            r, arq = self.roda(d, sys.executable, "-c", "import sys; print(sys.argv[1:]); sys.exit(3)", "--trace", "senha-secreta")
            self.assertEqual(r.returncode, 3)
            self.assertIn("['--trace', 'senha-secreta']", r.stdout)
            self.assertNotIn("senha-secreta", arq.read_text())
            self.assertEqual(json.loads(arq.read_text())["exit"], 3)

    def test_comando_inexistente_vira_127(self):
        with tempfile.TemporaryDirectory() as d:
            r, arq = self.roda(d, "comando-que-nao-existe-xyz")
            self.assertEqual((r.returncode, json.loads(arq.read_text())["exit"]), (127, 127))

    def test_registro_que_nao_grava_nao_muda_o_resultado(self):
        with tempfile.TemporaryDirectory() as d:
            r, _ = self.roda(d, sys.executable, "-c", "pass", extras=("--trace", d))
            self.assertEqual(r.returncode, 0)
            self.assertIn("não consegui gravar", r.stderr)


class VirarQuadro(unittest.TestCase):
    def test_replay_so_para_no_erro_se_nada_rodou_depois(self):
        seguiu = gravador.montar_spec([reg("a", 1, 1, ordem=1), reg("b", 2, ordem=2)])
        self.assertIsNone(seguiu["runs"][0]["breakAt"])
        self.assertIn("Falhou em “a”", seguiu["runs"][0]["note"])
        parou = gravador.montar_spec([reg("a", 1, ordem=1), reg("b", 2, 1, ordem=2)])
        self.assertEqual(parou["runs"][0]["breakAt"], "b")
        self.assertEqual(build.conferir(parou), [])

    def test_repeticao_soma_e_vale_o_ultimo_codigo(self):
        e = gravador.montar_spec([reg("a", 1, 1, ordem=1), reg("a", 2, 0, ordem=2)])["cards"][0]["steps"][0]
        self.assertEqual((e["seconds"], e["status"]), (3, None))
        self.assertIn("2 tentativas", e["metrics"][0]["note"])

    def test_junta_tempos_sem_apagar_o_que_veio_do_codigo(self):
        base = {"title": "x", "edges": [], "cards": [{"id": "coleta", "title": "Coleta", "steps": [
            {"id": "baixar", "name": "Baixar", "meta": gravador.LIDO, "flow": ["lê"]}, {"id": "outra", "name": "Outra", "meta": gravador.LIDO}]}]}
        uma = gravador.montar_spec([reg("Baixar", 5, grupo="Etapas")], base)
        duas = gravador.montar_spec([reg("Baixar", 7, grupo="Etapas")], uma)
        baixar, outra = duas["cards"][0]["steps"]
        self.assertEqual((baixar["flow"], baixar["seconds"], len(baixar["metrics"]), "meta" in baixar), (["lê"], 7, 1, False))
        self.assertEqual(outra["meta"], gravador.LIDO)
        self.assertEqual((len(duas["cards"]), build.conferir(duas)), (1, []))
        self.assertNotIn("seconds", base["cards"][0]["steps"][0])

    def test_nome_igual_em_grupos_diferentes_vira_duas_etapas(self):
        s = gravador.montar_spec([reg("testar", 1, grupo="web", ordem=1), reg("testar", 2, grupo="api", ordem=2)])
        self.assertEqual(len({e["id"] for c in s["cards"] for e in c["steps"]}), 2)
        self.assertEqual(build.conferir(s), [])

    def test_linha_cortada_e_ignorada_e_registro_vazio_recusado(self):
        bons, ruins = gravador.ler(json.dumps(reg("a", 1)) + '\n{"run": "r1", "na\n[1]\n')
        self.assertEqual((len(bons), ruins), (1, 2))
        with self.assertRaises(ValueError):
            gravador.montar_spec([])


if __name__ == "__main__":
    unittest.main()
