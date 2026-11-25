import json
import pathlib
import sys
import unittest

RAIZ = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "scripts"))
import build
import check
import collect

SPEC = {"title": "t", "cards": [{"id": "a", "title": "A", "steps": [{"id": "x", "name": "X"}]}]}


class Montagem(unittest.TestCase):
    def test_recusa_descricao_incoerente(self):
        ruim = {"cards": SPEC["cards"] * 2, "edges": [["a", "zz"]], "runs": [{"label": "r", "steps": ["x", "nada"], "seconds": [1]}]}
        erros = " | ".join(build.conferir(ruim))
        for trecho in ("cartão com id repetido", "etapa com id repetido", "seta para cartão", "etapa que não existe", "um valor por etapa"):
            self.assertIn(trecho, erros)
        self.assertEqual(build.conferir(SPEC), [])

    def test_falha_confirmada_exige_evidencia(self):
        base = {"title": "f", "status": "confirmed", "severity": "high", "step": "x"}
        erros = lambda **k: " | ".join(build.conferir({**SPEC, "findings": [{**base, **k}]}))
        self.assertIn("exige 'evidence'", erros())
        self.assertIn("exige 'evidence'", erros(evidence="  "))
        self.assertEqual(erros(evidence="linha 3"), "")
        self.assertEqual(erros(status="suspected"), "")
        self.assertIn("etapa que não existe", erros(evidence="a", step="zz"))
        self.assertIn("severity", erros(evidence="a", severity="enorme"))
        self.assertIn("status", erros(status="talvez"))

    def test_cadastro_e_icones_so_no_formato_esperado(self):
        erros = lambda **k: " | ".join(build.conferir({**SPEC, **k}))
        bom = {"items": [["g", "Org", "org", "conta"]], "form": {"repo": "o/r", "types": {"g": ["Conta", ""]}}}
        self.assertEqual(erros(catalog=bom), "")
        self.assertIn("catalog.items", erros(catalog={"items": [["g", "Org", 3, "x"]]}))
        self.assertIn("catalog.form", erros(catalog={**bom, "form": {"repo": "o/r?x=1", "types": {"g": ["a"]}}}))
        self.assertIn("ícone", erros(icons={"x": "https://mal.example/i.svg"}))
        html = build.montar({**SPEC, "icons": {"marca": "data:image/png;base64,AAAA"}, "cards": [{"id": "a", "title": "A", "steps": [{"id": "x", "name": "X", "icon": "marca"}]}]})
        self.assertEqual(html.count("data:image/png;base64,AAAA"), 1)

    def test_texto_de_log_nao_fecha_o_script(self):
        veneno = "</script><img src=x onerror=alert(1)> __SPEC__ __ICONS__"
        spec = {"title": veneno, "cards": [{"id": "a", "title": veneno, "steps": [{"id": "x", "name": veneno}]}]}
        html = build.montar(spec)
        self.assertEqual(html.count("</script>"), 1)
        self.assertNotIn("<img src=x", html)

    def test_exemplo_do_repositorio_monta(self):
        spec = json.loads((RAIZ / "examples" / "demo.spec.json").read_text())
        self.assertEqual(build.conferir(spec), [])

    def test_formato_de_artefato_nao_leva_a_casca_da_pagina(self):
        html = build.montar(SPEC, artefato=True)
        self.assertTrue(html.startswith("<title>"))
        for casca in ("<!doctype", "<html", "<head", "<body"):
            self.assertNotIn(casca, html)


class Trava(unittest.TestCase):
    def test_acha_segredo_sem_repetir_o_valor_inteiro(self):
        chave = "sk-" + "a1" * 20
        achados = check.procurar(f'{{"x":"{chave}","y":"fulano@empresa.com","z":"/Users/fulano/proj"}}')
        self.assertEqual(sorted(t for t, _ in achados), ["chave ou token", "e-mail", "pasta pessoal"])
        self.assertFalse(any(chave in trecho for _, trecho in achados))
        self.assertEqual(check.procurar('{"file":"jobs/orders.py","url":"https://example.org/a@2x.png"}'), [])

    def test_nome_de_empresa_e_endereco_de_site_nao_travam(self):
        self.assertEqual(check.procurar('["sk-hynix-south-korea","sk-group-south-korea","http://u.br/modulo/home/index.php"]'), [])
        for chave in ("sk-or-v1-" + "0a" * 24, "sk-ant-api03-" + "Ab1" * 12, "sk-proj-" + "x9" * 20):
            self.assertEqual([t for t, _ in check.procurar(f'"{chave}"')], ["chave ou token"], chave[:8])
        self.assertEqual([t for t, _ in check.procurar('"em /home/fulano/x"')], ["pasta pessoal"])


class Coleta(unittest.TestCase):
    def test_vira_cartoes_com_tempo_e_para_no_erro(self):
        passo = lambda n, c, a, b: {"name": n, "conclusion": c, "started_at": f"2026-01-01T00:0{a}:00Z", "completed_at": f"2026-01-01T00:0{b}:00Z"}
        execs = [{"id": 1, "name": "CI", "status": "completed", "conclusion": "failure", "run_started_at": "2026-01-01T00:00:00Z"},
                 {"id": 2, "name": "CI", "status": "completed", "conclusion": "success", "run_started_at": "2025-12-31T00:00:00Z"}]
        jobs = [{"name": "j", "steps": [passo("Set up job", "success", 0, 0), passo("Run actions/checkout@v4", "success", 0, 0), passo("Testes", "success", 0, 1), passo("Deploy", "failure", 1, 3), passo("Depois", "skipped", 3, 3)]}]
        s = collect.rascunho("o/r", execs, lambda i: jobs)
        etapas = s["cards"][0]["steps"]
        self.assertEqual([(e["name"], e["seconds"], e["status"]) for e in etapas], [("Testes", 60, None), ("Deploy", 120, "failed")])
        self.assertEqual(s["runs"][0]["breakAt"], etapas[1]["id"])
        self.assertIn("1 de 2", s["cards"][0]["summary"])
        self.assertEqual(build.conferir(s), [])


if __name__ == "__main__":
    unittest.main()
