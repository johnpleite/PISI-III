import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.aoty_eda import load_data, run_analysis


class LoadDataTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.csv_path = Path(self.temp_dir.name) / "albums.csv"
        pd.DataFrame(
            [
                {
                    "id": 1,
                    "title": "Álbum A",
                    "artist": "Artista A",
                    "release_date": "March 15, 2015",
                    "genres": "Rock, Indie Rock",
                    "user_score": 90,
                    "rating_count": "1,234 ratings",
                    "album_link": "https://example.com/1",
                },
                {
                    "id": 2,
                    "title": "Album B",
                    "artist": "Artist B",
                    "release_date": "1999",
                    "genres": "Pop",
                    "user_score": 80,
                    "rating_count": "456 ratings",
                    "album_link": "https://example.com/2",
                },
            ]
        ).to_csv(self.csv_path, index=False)

    def test_parses_scores_rating_counts_and_mixed_dates(self) -> None:
        data = load_data(self.csv_path)

        self.assertEqual(data["score"].tolist(), [90, 80])
        self.assertEqual(data["ratings"].tolist(), [1234, 456])
        self.assertEqual(data["release_year"].tolist(), [2015, 1999])
        self.assertEqual(data["decade"].tolist(), [2010, 1990])

    def test_rejects_missing_required_columns(self) -> None:
        pd.DataFrame({"id": [1]}).to_csv(self.csv_path, index=False)

        with self.assertRaisesRegex(ValueError, "Colunas obrigatórias ausentes"):
            load_data(self.csv_path)

    def test_rejects_invalid_nonempty_dates(self) -> None:
        data = pd.read_csv(self.csv_path)
        data.loc[0, "release_date"] = "not a date"
        data.to_csv(self.csv_path, index=False)

        with self.assertRaisesRegex(ValueError, "Datas inválidas"):
            load_data(self.csv_path)

    def test_generates_report_tables_and_charts(self) -> None:
        output_dir = Path(self.temp_dir.name) / "reports"

        run_analysis(self.csv_path, output_dir)

        self.assertTrue((output_dir / "relatorio.md").is_file())
        self.assertTrue((output_dir / "generos_mais_frequentes.csv").is_file())
        self.assertTrue((output_dir / "grupos_genero_nota.csv").is_file())
        album_groups = pd.read_csv(output_dir / "albuns_por_genero_faixa_nota.csv")
        self.assertEqual(len(album_groups), 3)
        self.assertEqual(
            set(album_groups.loc[album_groups["id"].eq(1), "genre"]),
            {"Rock", "Indie Rock"},
        )
        self.assertEqual(
            album_groups.loc[album_groups["id"].eq(1), "score_band"].unique().tolist(),
            ["90+"],
        )
        self.assertEqual(len(list((output_dir / "figuras").glob("*.png"))), 6)

    def test_script_runs_directly_with_custom_paths(self) -> None:
        output_dir = Path(self.temp_dir.name) / "cli-reports"
        script_path = Path(__file__).resolve().parents[1] / "src" / "aoty_eda.py"

        result = subprocess.run(
            [
                sys.executable,
                str(script_path),
                "--csv",
                str(self.csv_path),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue((output_dir / "relatorio.md").is_file())
        self.assertEqual(len(list((output_dir / "figuras").glob("*.png"))), 6)


if __name__ == "__main__":
    unittest.main()
