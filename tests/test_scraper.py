import unittest

from bs4 import BeautifulSoup

from scraper import _extract_bidders


class ScraperTests(unittest.TestCase):
    def test_extracts_bidders_from_multiline_table(self):
        html = """
        <html>
          <body>
            <table>
              <tr>
                <th>Entreprise</th>
                <th>Enveloppes administratives</th>
                <th>Enveloppes financières</th>
                <th colspan="2">Offre financière</th>
              </tr>
              <tr>
                <th></th>
                <th></th>
                <th></th>
                <th>Prix avant correction</th>
                <th>Prix après correction</th>
              </tr>
              <tr>
                <td>Societe Alpha</td>
                <td>Admissible</td>
                <td>Admissible</td>
                <td>100 000,00</td>
                <td>98 000,00</td>
              </tr>
            </table>
          </body>
        </html>
        """
        bidders = _extract_bidders(BeautifulSoup(html, "lxml"))
        self.assertEqual(len(bidders), 1)
        self.assertEqual(bidders[0].name, "Societe Alpha")
        self.assertEqual(bidders[0].price, 98000.0)


if __name__ == "__main__":
    unittest.main()
