import json
import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
import build
import collect


def passo(nome, seg, ruim=False):
    return {"name": nome, "conclusion": "failure" if ruim else "success", "started_at": "2026-01-01T00:00:00Z", "completed_at": f"2026-01-01T00:{seg // 60:02d}:{seg % 60:02d}Z"}


def coleta(rotinas):
    """{rotina: (dia, [passos])} em descrição, como o coletor faria."""
    execs = [{"id": i, "name": n, "status": "completed", "conclusion": "success", "run_started_at": f"2026-01-{dia:02d}T00:00:00Z"} for i, (n, (dia, _)) in enumerate(rotinas.items())]
    return collect.rascunho("o/r", execs, lambda i: [{"name": "j", "steps": list(rotinas.values())[i][1]}])


BASE = {"title": "meu", "edges": [["a", "b", "x"]], "findings": [{"title": "f", "status": "suspected", "severity": "low", "step": "baixar"}],
        "limits": [{"name": "l", "used": 1, "limit": 2}], "cards": [
    {"id": "a", "title": "Entrada", "col": 3, "steps": [{"id": "baixar", "name": "Baixar tudo", "ci": ["Diária :: Coleta", "Diária :: Preços"], "flow": ["meu fluxo"],
     "case": {"name": "c", "rows": []}, "metrics": [{"when": "à mão", "values": []}], "meta": collect.LIDO}]},
    {"id": "b", "title": "Saída", "steps": [{"id": "pub", "name": "Publica", "meta": "texto meu"}, {"id": "ideia", "name": "Sem rotina", "meta": collect.LIDO}]}]}


class Fundir(unittest.TestCase):
    def test_atualiza_numeros_e_preserva_o_que_foi_escrito(self):
        novo = coleta({"Diária": (2, [passo("Coleta", 60), passo("Preços", 5), passo("Publica", 30), passo("Passo novo", 1)])})
        spec, sobra = collect.fundir(BASE, novo)
        baixar, pub, ideia = collect.etapas_de(spec)
        self.assertEqual((baixar["seconds"], baixar["flow"], baixar["case"]["name"]), (65, ["meu fluxo"], "c"))
        self.assertEqual([m["when"] for m in baixar["metrics"]], ["execução de 2026-01-02 · Diária", "à mão"])
        self.assertNotIn("meta", baixar)
        self.assertEqual((pub["seconds"], pub["meta"], ideia["meta"]), (30, "texto meu", collect.LIDO))
        for campo in ("edges", "findings", "limits", "title"):
            self.assertEqual(spec[campo], BASE[campo])
        self.assertEqual(spec["cards"][0]["col"], 3)
        self.assertEqual(sobra, ["Diária :: Passo novo"])
        self.assertEqual((spec["runs"][0]["steps"], spec["runs"][0]["seconds"]), (["baixar", "pub"], [65, 30]))
        self.assertEqual(build.conferir(spec), [])
        self.assertNotIn("ci", BASE["cards"][1]["steps"][0])

    def test_repetir_nao_acumula_e_falha_vai_e_volta(self):
        ruim, _ = collect.fundir(BASE, coleta({"Diária": (2, [passo("Coleta", 60), passo("Publica", 30, True)])}))
        self.assertEqual((ruim["cards"][1]["tone"], ruim["runs"][0]["breakAt"]), ("warn", "pub"))
        bom, _ = collect.fundir(ruim, coleta({"Diária": (3, [passo("Coleta", 7), passo("Publica", 8)])}))
        baixar, pub, _i = collect.etapas_de(bom)
        self.assertEqual((baixar["seconds"], len(baixar["metrics"]), pub["status"], bom["cards"][1]["tone"], len(bom["runs"])), (7, 2, None, "", 1))

    def test_passo_que_sumiu_nao_fica_com_tempo_velho(self):
        antes, _ = collect.fundir(BASE, coleta({"Diária": (2, [passo("Coleta", 60), passo("Publica", 30)])}))
        depois, _ = collect.fundir(antes, coleta({"Diária": (3, [passo("Coleta", 61)])}))
        pub = collect.etapas_de(depois)[1]
        self.assertEqual((pub.get("seconds"), pub["meta"]), (None, collect.NAO_RODOU))

    def test_rotina_que_nao_veio_fica_como_estava_e_a_mais_nova_vale(self):
        duas = coleta({"Diária": (2, [passo("Publica", 30)]), "Semanal": (5, [passo("Publica", 99)])})
        spec, _ = collect.fundir(BASE, duas)
        self.assertEqual(collect.etapas_de(spec)[1]["seconds"], 99)
        so_outra, _ = collect.fundir(spec, coleta({"Outra": (6, [passo("x", 1)])}))
        self.assertEqual(collect.etapas_de(so_outra)[1]["seconds"], 99)
        self.assertEqual(sorted(r["label"] for r in so_outra["runs"]), ["Diária", "Semanal"])


if __name__ == "__main__":
    unittest.main()
