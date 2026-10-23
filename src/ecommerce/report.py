"""Gera os gráficos estáticos usados no README a partir do banco DuckDB."""

from __future__ import annotations

from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
BLUE, RED, GRAY = "#2563eb", "#dc2626", "#9ca3af"


def _style(ax):
    ax.spines[["top", "right"]].set_visible(False)


def make_figures(db_path: Path, out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path), read_only=True)
    paths = []

    df = con.sql("SELECT mes, receita / 1000 AS receita FROM mart_receita_mensal").df()
    fig, ax = plt.subplots(figsize=(8, 3.8))
    colors = [RED if m.month == 11 else BLUE for m in df["mes"]]
    ax.bar(df["mes"], df["receita"], width=20, color=colors)
    ax.set_ylabel("Receita (R$ mil)")
    ax.set_title("Receita mensal (novembro em vermelho: Black Friday)")
    _style(ax)
    fig.tight_layout()
    paths.append(out / "receita_mensal.png")
    fig.savefig(paths[-1], dpi=150)
    plt.close(fig)

    df = con.sql("SELECT * FROM mart_atraso_vs_nota").df()
    labels = [f[3:] for f in df["faixa_atraso"]]
    fig, ax = plt.subplots(figsize=(8, 3.8))
    bars = ax.bar(labels, df["nota_media"], color=[BLUE, BLUE, GRAY, RED, RED])
    ax.bar_label(bars, fmt="%.2f", padding=3)
    ax.set_ylim(0, 5)
    ax.set_ylabel("Nota média (1 a 5)")
    ax.set_title("Atraso na entrega derruba a avaliação do cliente")
    ax.tick_params(axis="x", labelsize=8)
    _style(ax)
    fig.tight_layout()
    paths.append(out / "atraso_vs_nota.png")
    fig.savefig(paths[-1], dpi=150)
    plt.close(fig)

    df = con.sql("""SELECT estado, taxa_atraso * 100 AS taxa FROM mart_entregas_estado
                    WHERE pedidos_entregues >= 30 ORDER BY taxa""").df()
    fig, ax = plt.subplots(figsize=(8, 5.5))
    colors = [RED if t > 10 else BLUE for t in df["taxa"]]
    ax.barh(df["estado"], df["taxa"], color=colors)
    ax.set_xlabel("% dos pedidos entregues com atraso")
    ax.set_title("Taxa de atraso por estado (estados com 30+ pedidos)")
    ax.tick_params(axis="y", labelsize=8)
    _style(ax)
    fig.tight_layout()
    paths.append(out / "atraso_por_estado.png")
    fig.savefig(paths[-1], dpi=150)
    plt.close(fig)

    con.close()
    return paths


if __name__ == "__main__":
    for p in make_figures(ROOT / "data" / "ecommerce.duckdb", ROOT / "reports" / "figures"):
        print(p.relative_to(ROOT))
