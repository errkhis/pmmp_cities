import unittest

from company_city import CompanyCity, _best_match, _clean_search_name


class CompanyCityTests(unittest.TestCase):
    def test_clean_search_name_removes_legal_form(self):
        self.assertEqual(_clean_search_name("STE ALPHA SARL AU"), "ALPHA")

    def test_best_match_prefers_exact_normalized_name(self):
        rows = [
            {"denomination": "BETA SARL", "libelle": "Casablanca"},
            {"denomination": "ALPHA SARL AU", "libelle": "Safi"},
        ]
        row = _best_match("STE ALPHA", rows)
        self.assertEqual(row["libelle"], "Safi")

    def test_company_city_dataclass(self):
        item = CompanyCity(name="A", city=None, matched_name=None)
        self.assertIsNone(item.city)


if __name__ == "__main__":
    unittest.main()
