from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SCORE_BAND_ORDER = ["<80", "80-<85", "85-<90", "90+", "Sem nota"]
SCORE_BINS = [float("-inf"), 80, 85, 90, float("inf")]
SCORE_BAND_LABELS = SCORE_BAND_ORDER[:-1]
REQUIRED_COLUMNS = {
    "id",
    "title",
    "artist",
    "release_date",
    "genres",
    "user_score",
    "rating_count",
    "album_link",
}


def load_data(csv_path: Path) -> pd.DataFrame:
    """Load the album CSV and add validated numeric/date columns for analysis."""
    if not csv_path.is_file():
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_path}")

    data = pd.read_csv(csv_path)
    missing_columns = REQUIRED_COLUMNS.difference(data.columns)
    if missing_columns:
        names = ", ".join(sorted(missing_columns))
        raise ValueError(f"Colunas obrigatórias ausentes no CSV: {names}")
    if data.empty:
        raise ValueError("O arquivo CSV não contém registros.")

    data["score"] = pd.to_numeric(data["user_score"], errors="coerce")
    invalid_scores = data["user_score"].notna() & data["score"].isna()
    if invalid_scores.any():
        examples = data.loc[invalid_scores, "user_score"].astype(str).head(5).tolist()
        raise ValueError(f"Notas inválidas em user_score: {examples}")

    rating_text = (
        data["rating_count"]
        .astype("string")
        .str.extract(r"([\d,]+)", expand=False)
        .str.replace(",", "", regex=False)
    )
    data["ratings"] = pd.to_numeric(rating_text, errors="coerce")
    invalid_ratings = data["rating_count"].notna() & data["ratings"].isna()
    if invalid_ratings.any():
        examples = data.loc[invalid_ratings, "rating_count"].astype(str).head(5).tolist()
        raise ValueError(f"Contagens inválidas em rating_count: {examples}")

    data["release_date_parsed"] = pd.to_datetime(
        data["release_date"], format="mixed", errors="coerce"
    )
    invalid_dates = data["release_date"].notna() & data["release_date_parsed"].isna()
    if invalid_dates.any():
        examples = data.loc[invalid_dates, "release_date"].astype(str).head(5).tolist()
        raise ValueError(f"Datas inválidas em release_date: {examples}")

    data["release_year"] = data["release_date_parsed"].dt.year
    data["decade"] = (data["release_year"] // 10) * 10
    return data


def _build_genre_groups(data: pd.DataFrame) -> pd.DataFrame:
    """Assign each album to every listed genre and to one score band."""
    genre_rows = data.dropna(subset=["genres"]).copy()
    genre_rows["genre"] = genre_rows["genres"].str.split(",")
    genre_rows = genre_rows.explode("genre")
    genre_rows["genre"] = genre_rows["genre"].str.strip()
    genre_rows = genre_rows[genre_rows["genre"].ne("")]
    genre_rows = genre_rows.drop_duplicates(subset=["id", "genre"])
    score_bands = pd.cut(
        genre_rows["score"],
        bins=SCORE_BINS,
        labels=SCORE_BAND_LABELS,
        right=False,
    )
    genre_rows["score_band"] = (
        score_bands.cat.add_categories(["Sem nota"]).fillna("Sem nota")
    )
    return genre_rows


def _save_charts(
    data: pd.DataFrame,
    output_dir: Path,
    genre_counts: pd.Series,
    genre_rows: pd.DataFrame,
    decade_summary: pd.DataFrame,
    score_rating_correlation: float,
) -> None:
    figures_dir = output_dir / "figuras"
    figures_dir.mkdir(parents=True, exist_ok=True)

    scores = data["score"].dropna()
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.hist(scores, bins=range(74, 97), color="#4C78A8", edgecolor="white", align="left")
    if not scores.empty:
        ax.axvline(scores.mean(), color="#E45756", linestyle="--", label=f"Média: {scores.mean():.2f}")
        ax.axvline(scores.median(), color="#54A24B", linestyle=":", label=f"Mediana: {scores.median():.0f}")
        ax.legend()
    ax.set(title="Distribuição das notas dos usuários", xlabel="Nota", ylabel="Número de álbuns")
    ax.set_xticks(range(75, 96, 2))
    fig.tight_layout()
    fig.savefig(figures_dir / "01_distribuicao_notas.png", dpi=150)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    if not decade_summary.empty:
        ax.bar(
            decade_summary.index.astype(str) + "s",
            decade_summary["album_count"],
            color="#72B7B2",
        )
    ax.set(title="Álbuns por década de lançamento", xlabel="Década", ylabel="Número de álbuns")
    ax.tick_params(axis="x", rotation=35)
    fig.tight_layout()
    fig.savefig(figures_dir / "02_albuns_por_decada.png", dpi=150)
    plt.close(fig)

    top_genres = genre_counts.head(10).sort_values()
    fig, ax = plt.subplots(figsize=(10, 6))
    if not top_genres.empty:
        ax.barh(top_genres.index, top_genres.values, color="#F2CF5B")
    ax.set(title="10 gêneros mais frequentes", xlabel="Número de álbuns", ylabel="Gênero")
    fig.tight_layout()
    fig.savefig(figures_dir / "03_generos_frequentes.png", dpi=150)
    plt.close(fig)

    paired = data.dropna(subset=["score", "ratings"])
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.scatter(paired["score"], paired["ratings"], alpha=0.35, color="#B279A2", edgecolors="none")
    if not paired.empty and (paired["ratings"] > 0).any():
        ax.set_yscale("log")
    ax.set(
        title=f"Nota e número de avaliações (ρ de Spearman = {score_rating_correlation:.2f})",
        xlabel="Nota dos usuários",
        ylabel="Número de avaliações (escala logarítmica)",
    )
    fig.tight_layout()
    fig.savefig(figures_dir / "04_nota_vs_avaliacoes.png", dpi=150)
    plt.close(fig)

    top_genre_names = genre_counts.head(15).index
    score_distribution = pd.crosstab(
        genre_rows["genre"], genre_rows["score_band"], normalize="index"
    )
    score_distribution = (
        score_distribution.reindex(index=top_genre_names, fill_value=0)
        .reindex(columns=SCORE_BAND_ORDER, fill_value=0)
        .drop(columns="Sem nota")
        * 100
    )
    fig, ax = plt.subplots(figsize=(10, max(5, len(score_distribution) * 0.38)))
    if not score_distribution.empty:
        image = ax.imshow(score_distribution.to_numpy(), aspect="auto", cmap="YlGnBu", vmin=0, vmax=100)
        ax.set_yticks(range(len(score_distribution)), labels=score_distribution.index)
        ax.set_xticks(range(len(score_distribution.columns)), labels=score_distribution.columns)
        for row_index in range(len(score_distribution)):
            for column_index in range(len(score_distribution.columns)):
                value = score_distribution.iat[row_index, column_index]
                ax.text(
                    column_index,
                    row_index,
                    f"{value:.0f}%",
                    ha="center",
                    va="center",
                    color="white" if value >= 55 else "black",
                    fontsize=8,
                )
        fig.colorbar(image, ax=ax, label="Percentual dos álbuns do gênero")
    ax.set(
        title="Faixas de nota dentro dos 15 gêneros mais frequentes",
        xlabel="Faixa da nota agregada",
        ylabel="Gênero",
    )
    fig.tight_layout()
    fig.savefig(figures_dir / "05_genero_por_faixa_nota.png", dpi=150)
    plt.close(fig)

    top_boxplot_genres = genre_counts.head(12).index
    score_groups = [
        genre_rows.loc[genre_rows["genre"].eq(genre), "score"].dropna()
        for genre in top_boxplot_genres
    ]
    nonempty_groups = [
        (genre, scores) for genre, scores in zip(top_boxplot_genres, score_groups) if not scores.empty
    ]
    fig, ax = plt.subplots(figsize=(12, 6))
    if nonempty_groups:
        ax.boxplot(
            [scores for _, scores in nonempty_groups],
            showfliers=False,
        )
        ax.set_xticks(
            range(1, len(nonempty_groups) + 1),
            labels=[genre for genre, _ in nonempty_groups],
        )
        ax.tick_params(axis="x", rotation=40)
    ax.set(
        title="Distribuição das notas por gênero (12 mais frequentes)",
        xlabel="Gênero",
        ylabel="Nota agregada do álbum",
    )
    fig.tight_layout()
    fig.savefig(figures_dir / "06_notas_por_genero.png", dpi=150)
    plt.close(fig)


def _write_report(
    data: pd.DataFrame,
    output_dir: Path,
    genre_counts: pd.Series,
    genre_group_summary: pd.DataFrame,
    artist_counts: pd.Series,
    decade_summary: pd.DataFrame,
    score_rating_correlation: float,
) -> None:
    scores = data["score"].dropna()
    ratings = data["ratings"].dropna()
    release_years = data["release_year"].dropna()
    top_artist = artist_counts.index[0] if not artist_counts.empty else "—"
    top_genre = genre_counts.index[0] if not genre_counts.empty else "—"
    most_rated = data.loc[data["ratings"].idxmax()] if ratings.size else None
    strongest_groups = (
        genre_group_summary[genre_group_summary["album_count"].ge(10)]
        .sort_values(["mean_score", "album_count"], ascending=[False, False])
        .head(5)
    )
    missing_cells = int(data[list(REQUIRED_COLUMNS)].isna().sum().sum())
    duplicate_ids = int(data["id"].duplicated().sum())
    duplicate_links = int(data["album_link"].duplicated().sum())

    lines = [
        "# Relatório de análise exploratória — Album of the Year",
        "",
        "## Visão geral",
        "",
        f"- Registros: **{len(data):,}**",
        f"- Colunas originais: **{len(REQUIRED_COLUMNS)}**",
        f"- Células vazias nas colunas originais: **{missing_cells:,}**",
        f"- IDs duplicados: **{duplicate_ids:,}**",
        f"- Links duplicados: **{duplicate_links:,}**",
        (
            f"- Intervalo de anos de lançamento: **{int(release_years.min())}–"
            f"{int(release_years.max())}**"
            if not release_years.empty
            else "- Intervalo de anos de lançamento: indisponível"
        ),
        "",
        "## Principais resultados",
        "",
        (
            f"- Nota média: **{scores.mean():.2f}**; mediana: **{scores.median():.1f}**; "
            f"intervalo observado: **{scores.min():.0f}–{scores.max():.0f}**."
            if not scores.empty
            else "- Não há notas válidas para resumir."
        ),
        (
            f"- Avaliações por álbum: mediana de **{ratings.median():,.0f}** e média de "
            f"**{ratings.mean():,.0f}**."
            if not ratings.empty
            else "- Não há contagens de avaliações válidas para resumir."
        ),
        f"- Artista com mais álbuns no conjunto: **{top_artist}** ({int(artist_counts.iloc[0]) if not artist_counts.empty else 0} álbuns).",
        f"- Gênero mais frequente: **{top_genre}** ({int(genre_counts.iloc[0]) if not genre_counts.empty else 0} ocorrências).",
        f"- Correlação de Spearman entre nota e quantidade de avaliações: **{score_rating_correlation:.3f}**.",
        (
            f"- Álbum com mais avaliações: **{most_rated['title']}**, de {most_rated['artist']} "
            f"({int(most_rated['ratings']):,} avaliações; nota {most_rated['score']:.0f})."
            if most_rated is not None
            else "- Não há álbum com contagem de avaliações válida."
        ),
        "",
        "A correlação descreve uma associação monotônica neste conjunto; não demonstra causalidade. "
        "A distribuição também é influenciada pela seleção de álbuns e usuários da fonte.",
        "",
        "## Grupos para descoberta por gênero e nota",
        "",
        "- Cada álbum é associado a cada gênero informado (um álbum com vários gêneros aparece em vários grupos) e a uma faixa de nota: `<80`, `80-<85`, `85-<90` ou `90+`.",
        "- Use `albuns_por_genero_faixa_nota.csv` para explorar álbuns de um gênero; dentro de cada grupo, os registros são ordenados por nota e depois por quantidade de avaliações.",
        "- O mapa de calor compara a proporção de notas em cada gênero; os boxplots mostram a distribuição das notas nos gêneros mais frequentes.",
        (
            "- Entre grupos com pelo menos 10 álbuns, as maiores médias de nota foram: "
            + "; ".join(
                f"**{row.genre} ({row.score_band})** — média {row.mean_score:.2f} "
                f"em {int(row.album_count)} álbuns"
                for row in strongest_groups.itertuples(index=False)
            )
            + "."
            if not strongest_groups.empty
            else "- Não há grupos com pelo menos 10 álbuns para comparar."
        ),
        "- Esses grupos são uma forma transparente de filtrar candidatos por conteúdo e nota agregada, não clusters aprendidos nem uma probabilidade comprovada de agrado. A confirmação exige histórico e avaliação com usuários.",
        "",
        "![Faixas de nota por gênero](figuras/05_genero_por_faixa_nota.png)",
        "",
        "![Distribuição de notas por gênero](figuras/06_notas_por_genero.png)",
        "",
        "## Gráficos",
        "",
        "![Distribuição das notas](figuras/01_distribuicao_notas.png)",
        "",
        "![Álbuns por década](figuras/02_albuns_por_decada.png)",
        "",
        "![Gêneros frequentes](figuras/03_generos_frequentes.png)",
        "",
        "![Nota e quantidade de avaliações](figuras/04_nota_vs_avaliacoes.png)",
        "",
        "## Arquivos tabulares",
        "",
        "- `artistas_mais_frequentes.csv` — artistas com mais álbuns.",
        "- `generos_mais_frequentes.csv` — frequência e nota média por gênero.",
        "- `albuns_por_decada.csv` — quantidade de álbuns e nota média por década.",
        "- `grupos_genero_nota.csv` — resumo dos grupos de gênero por faixa de nota.",
        "- `albuns_por_genero_faixa_nota.csv` — álbuns atribuídos aos grupos, ordenados por nota e avaliações.",
        "",
        "Datas com formatos variados são interpretadas durante a leitura; a comparação temporal "
        "usa apenas o ano extraído.",
    ]
    (output_dir / "relatorio.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_analysis(csv_path: Path, output_dir: Path) -> None:
    data = load_data(csv_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    artist_counts = data["artist"].dropna().value_counts().rename_axis("artist")
    artist_counts.rename("album_count").head(20).to_csv(
        output_dir / "artistas_mais_frequentes.csv", encoding="utf-8-sig"
    )

    genre_rows = _build_genre_groups(data)
    genre_summary = (
        genre_rows.groupby("genre")
        .agg(album_count=("id", "nunique"), mean_score=("score", "mean"))
        .sort_values(["album_count", "mean_score"], ascending=[False, False])
    )
    genre_summary.to_csv(output_dir / "generos_mais_frequentes.csv", encoding="utf-8-sig")

    genre_group_summary = (
        genre_rows.groupby(["genre", "score_band"], observed=True)
        .agg(
            album_count=("id", "nunique"),
            mean_score=("score", "mean"),
            median_score=("score", "median"),
            median_ratings=("ratings", "median"),
        )
        .reset_index()
        .sort_values(["genre", "score_band"])
    )
    genre_group_summary.to_csv(
        output_dir / "grupos_genero_nota.csv", index=False, encoding="utf-8-sig"
    )
    album_group_columns = [
        "id",
        "title",
        "artist",
        "genre",
        "score_band",
        "score",
        "ratings",
        "release_year",
        "album_link",
    ]
    genre_rows.sort_values(
        ["genre", "score", "ratings"],
        ascending=[True, False, False],
        na_position="last",
    )[album_group_columns].to_csv(
        output_dir / "albuns_por_genero_faixa_nota.csv",
        index=False,
        encoding="utf-8-sig",
    )

    decade_summary = (
        data.dropna(subset=["decade"])
        .groupby("decade")
        .agg(album_count=("id", "size"), mean_score=("score", "mean"))
        .sort_index()
    )
    decade_summary.to_csv(output_dir / "albuns_por_decada.csv", encoding="utf-8-sig")

    paired = data[["score", "ratings"]].dropna()
    correlation = (
        float(paired["score"].rank().corr(paired["ratings"].rank()))
        if len(paired) > 1
        else float("nan")
    )

    _save_charts(
        data,
        output_dir,
        genre_summary["album_count"],
        genre_rows,
        decade_summary,
        correlation,
    )
    _write_report(
        data,
        output_dir,
        genre_summary["album_count"],
        genre_group_summary,
        artist_counts,
        decade_summary,
        correlation,
    )
    print(f"Análise concluída. Relatório disponível em: {output_dir / 'relatorio.md'}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gera tabelas, gráficos e relatório exploratório do dataset AOTY."
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=ROOT / "data" / "aoty.csv",
        help="Caminho do arquivo CSV (padrão: data/aoty.csv).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "reports",
        help="Pasta de saída (padrão: reports/).",
    )
    args = parser.parse_args()
    run_analysis(args.csv, args.output_dir)


if __name__ == "__main__":
    main()
