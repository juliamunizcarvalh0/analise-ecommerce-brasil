"""Pipeline ELT: carrega os CSVs brutos no DuckDB, roda os modelos SQL e
valida a qualidade dos dados.

Uso:
    python -m ecommerce.pipeline                     # usa data/raw e data/ecommerce.duckdb
    python -m ecommerce.pipeline --raw outra/pasta
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path

import duckdb

from .generate import RAW_FILES

ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = ROOT / "sql"
MART_TABLES = [
    "fct_pedidos", "mart_receita_mensal", "mart_entregas_estado",
    "mart_atraso_vs_nota", "mart_categorias", "mart_rfm", "mart_coortes",
]


class DataQualityError(Exception):
    """Algum teste de qualidade de dados falhou."""


@dataclass
class Check:
    name: str
    sql: str  # deve retornar 0 linhas / o valor 0 quando estiver tudo certo


CHECKS = [
    Check("pedido_id é único em fct_pedidos",
          "SELECT count(*) - count(DISTINCT pedido_id) FROM fct_pedidos"),
    Check("todo pedido tem cliente e estado",
          "SELECT count(*) FROM fct_pedidos WHERE cliente_id IS NULL OR estado IS NULL"),
    Check("estados são siglas válidas (2 letras)",
          "SELECT count(*) FROM fct_pedidos WHERE length(estado) <> 2"),
    Check("valores não negativos",
          "SELECT count(*) FROM fct_pedidos WHERE valor_produtos < 0 OR valor_frete < 0"),
    Check("notas entre 1 e 5",
          "SELECT count(*) FROM fct_pedidos WHERE nota NOT BETWEEN 1 AND 5"),
    Check("entrega não acontece antes da compra",
          "SELECT count(*) FROM fct_pedidos WHERE entregue_em < comprado_em"),
    Check("pagamento confere com itens + frete (tolerância de 1%)",
          """SELECT count(*) FROM fct_pedidos f JOIN stg_pagamentos p USING (pedido_id)
             WHERE abs(p.valor_pago - f.valor_total) > 0.01 * f.valor_total + 0.05"""),
    Check("receita mensal bate com a tabela fato",
          """SELECT abs((SELECT sum(receita) FROM mart_receita_mensal) -
                        (SELECT sum(valor_total) FROM fct_pedidos
                         WHERE status NOT IN ('canceled', 'unavailable'))) > 1"""),
    Check("retenção da coorte no mês 0 é 100%",
          "SELECT count(*) FROM mart_coortes WHERE meses_desde_primeira = 0 AND retencao <> 1"),
]


def load_raw(con: duckdb.DuckDBPyConnection, raw_dir: Path) -> None:
    for name, filename in RAW_FILES.items():
        path = raw_dir / filename
        if not path.exists():
            raise FileNotFoundError(
                f"Arquivo {path} não encontrado. Rode `python -m ecommerce.generate` "
                "ou copie os CSVs originais da Olist para essa pasta."
            )
        con.execute(
            f"CREATE OR REPLACE TABLE raw_{name} AS SELECT * FROM read_csv_auto(?)",
            [str(path)],
        )


def run_sql_models(con: duckdb.DuckDBPyConnection, sql_dir: Path = SQL_DIR) -> list[str]:
    executed = []
    for layer in ("staging", "marts"):
        for file in sorted((sql_dir / layer).glob("*.sql")):
            con.execute(file.read_text(encoding="utf-8"))
            executed.append(f"{layer}/{file.name}")
    return executed


def run_checks(con: duckdb.DuckDBPyConnection) -> list[tuple[str, bool]]:
    results = []
    for check in CHECKS:
        value = con.execute(check.sql).fetchall()[0][0]
        results.append((check.name, not value))
    failed = [name for name, ok in results if not ok]
    if failed:
        raise DataQualityError("Falhou: " + "; ".join(failed))
    return results


def run(raw_dir: Path, db_path: Path, verbose: bool = True) -> duckdb.DuckDBPyConnection:
    start = time.perf_counter()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(db_path))
    load_raw(con, raw_dir)
    models = run_sql_models(con)
    checks = run_checks(con)
    if verbose:
        print(f"{len(models)} modelos SQL executados:")
        for m in models:
            print(f"  ✓ {m}")
        print(f"\n{len(checks)} testes de qualidade:")
        for name, _ in checks:
            print(f"  ✓ {name}")
        print()
        for table in MART_TABLES:
            n = con.execute(f"SELECT count(*) FROM {table}").fetchall()[0][0]
            print(f"  {table:24s} {n:>8,} linhas")
        print(f"\nConcluído em {time.perf_counter() - start:.1f}s → {db_path}")
    return con


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw", type=Path, default=ROOT / "data" / "raw")
    parser.add_argument("--db", type=Path, default=ROOT / "data" / "ecommerce.duckdb")
    args = parser.parse_args()
    run(args.raw, args.db).close()


if __name__ == "__main__":
    main()
