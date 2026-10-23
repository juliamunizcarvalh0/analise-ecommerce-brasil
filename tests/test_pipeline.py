import pandas as pd
import pytest

from ecommerce import generate, pipeline


@pytest.fixture(scope="module")
def con(tmp_path_factory):
    """Pipeline completo sobre uma amostra sintética pequena."""
    tmp = tmp_path_factory.mktemp("ecom")
    generate.write(generate.generate(n_orders=4000, seed=11), tmp / "raw")
    c = pipeline.run(tmp / "raw", tmp / "db.duckdb", verbose=False)
    yield c
    c.close()


def test_all_marts_are_built(con):
    for table in pipeline.MART_TABLES:
        assert con.execute(f"SELECT count(*) FROM {table}").fetchall()[0][0] > 0


def test_late_deliveries_get_worse_reviews(con):
    notas = con.sql("SELECT nota_media FROM mart_atraso_vs_nota ORDER BY faixa_atraso").df()
    on_time, very_late = notas["nota_media"].iloc[1], notas["nota_media"].iloc[-1]
    assert very_late < on_time - 1


def test_november_is_the_best_month(con):
    df = con.sql("SELECT mes, receita FROM mart_receita_mensal").df()
    top = df.loc[df["receita"].idxmax(), "mes"]
    assert pd.Timestamp(top).month == 11


def test_rfm_segments_cover_every_customer(con):
    n_rfm = con.execute("SELECT count(*) FROM mart_rfm").fetchall()[0][0]
    n_clientes = con.execute("""SELECT count(DISTINCT cliente_id) FROM fct_pedidos
                                WHERE status NOT IN ('canceled','unavailable')""").fetchall()[0][0]
    assert n_rfm == n_clientes


def test_missing_raw_file_has_clear_error(tmp_path):
    with pytest.raises(FileNotFoundError, match="ecommerce.generate"):
        pipeline.run(tmp_path, tmp_path / "db.duckdb", verbose=False)
