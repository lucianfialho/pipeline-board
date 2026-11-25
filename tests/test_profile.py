import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "scripts"))
# o módulo `profile` da biblioteca padrão tem o mesmo nome; o caminho acima precisa ganhar dele
sys.modules.pop("profile", None)
import profile as perfil


class Perfil(unittest.TestCase):
    def test_acha_corte_escondido_na_soma_de_donos_sem_mostrar_registros(self):
        dado = {f"org{i}": {"itens": [{"id": "x/segredo"}]} for i in range(40)}
        dado["grande"] = {"itens": [{"id": f"a/{n}"} for n in range(1000)] + [{"id": f"b/{n}"} for n in range(7)]}
        achados, _ = perfil.analisar(dado)
        texto = " ".join(a for a, _ in achados)
        self.assertIn("1000 itens de 'a'", texto)
        self.assertNotIn("segredo", texto)
        self.assertNotIn("grande", texto)

    def test_tamanho_comum_nao_vira_indicio(self):
        achados, _ = perfil.analisar({"a": list(range(37)), "b": [{"id": f"a/{n}"} for n in range(999)]})
        self.assertEqual(achados, [])


if __name__ == "__main__":
    unittest.main()
