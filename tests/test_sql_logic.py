"""Testes das regras de negócio do SQL com dados minúsculos montados à mão."""

import duckdb
import pandas as pd
import pytest

from ecommerce import pipeline


def _tables():
    orders = pd.DataFrame({
        "order_id": ["A", "B", "C"],
        "customer_id": ["c1", "c2", "c3"],
        "order_status": ["delivered", "delivered", "canceled"],
        "order_purchase_timestamp": pd.to_datetime(["2024-01-05", "2024-01-10", "2024-02-01"]),
        "order_approved_at": pd.to_datetime(["2024-01-05", "2024-01-10", None]),
        "order_delivered_carrier_date": pd.to_datetime(["2024-01-06", "2024-01-11", None]),
        "order_delivered_customer_date": pd.to_datetime(["2024-01-12", "2024-01-25", None]),
        "order_estimated_delivery_date": pd.to_datetime(["2024-01-20", "2024-01-20", "2024-02-15"]),
    })
    customers = pd.DataFrame({
        "customer_id": ["c1", "c2", "c3"],
        # c1 e c2 são a mesma pessoa (mesmo customer_unique_id), como na Olist.
        "customer_unique_id": ["pessoa1", "pessoa1", "pessoa2"],
        "customer_zip_code_prefix": [1000, 1000, 2000],
        "customer_city": ["sao paulo", "sao paulo", "recife"],
        "customer_state": ["sp", "SP", "PE"],
    })
    items = pd.DataFrame({
        "order_id": ["A", "A", "B", "C"],
        "order_item_id": [1, 2, 1, 1],
        "product_id": ["p1", "p2", "p1", "p2"],
        "seller_id": ["s1"] * 4,
        "shipping_limit_date": pd.to_datetime(["2024-01-08"] * 4),
        "price": [100.0, 50.0, 100.0, 50.0],
        "freight_value": [10.0, 5.0, 10.0, 5.0],
    })
    products = pd.DataFrame({"product_id": ["p1", "p2"],
                             "product_category_name": ["audio", None],
                             "product_weight_g": [500, 300]})
    payments = pd.DataFrame({
        "order_id": ["A", "A", "B", "C"],
        "payment_sequential": [1, 2, 1, 1],
        "payment_type": ["credit_card", "voucher", "pix", "boleto"],
        "payment_installments": [3, 1, 1, 1],
        "payment_value": [150.0, 15.0, 110.0, 55.0],
    })
    reviews = pd.DataFrame({
        "review_id": ["r1", "r2", "r3"],
        "order_id": ["A", "A", "B"],
        "review_score": [2, 5, 1],
        "review_creation_date": pd.to_datetime(["2024-01-13", "2024-01-15", "2024-01-26"]),
    })
    return {"orders": orders, "customers": customers, "order_items": items,
            "products": products, "payments": payments, "reviews": reviews}


@pytest.fixture()
def con():
    c = duckdb.connect()
    for name, df in _tables().items():
        c.register(f"df_{name}", df)
        c.execute(f"CREATE TABLE raw_{name} AS SELECT * FROM df_{name}")
    pipeline.run_sql_models(c)
    yield c
    c.close()


def _fct(con) -> pd.DataFrame:
    return con.sql("SELECT * FROM fct_pedidos ORDER BY pedido_id").df().set_index("pedido_id")


def test_order_totals_and_main_category(con):
    f = _fct(con)
    assert f.loc["A", "qtd_itens"] == 2
    assert f.loc["A", "valor_total"] == pytest.approx(165.0)
    assert f.loc["A", "categoria_principal"] == "audio"      # item mais caro
    assert f.loc["C", "categoria_principal"] == "sem_categoria"


def test_main_payment_is_the_largest_one(con):
    f = _fct(con)
    assert f.loc["A", "forma_pagamento"] == "credit_card"
    assert f.loc["A", "parcelas"] == 3


def test_keeps_only_latest_review(con):
    assert _fct(con).loc["A", "nota"] == 5


def test_delay_calculation(con):
    f = _fct(con)
    assert f.loc["A", "atraso_dias"] == -8 and not f.loc["A", "atrasado"]
    assert f.loc["B", "atraso_dias"] == 5 and f.loc["B", "atrasado"]


def test_state_is_uppercased_and_people_are_deduplicated(con):
    f = _fct(con)
    assert set(f["estado"]) == {"SP", "PE"}
    rfm = con.sql("SELECT * FROM mart_rfm").df().set_index("cliente_id")
    # pessoa1 fez 2 pedidos válidos; pessoa2 só tem um pedido cancelado.
    assert rfm.loc["pessoa1", "frequencia"] == 2
    assert "pessoa2" not in rfm.index


def test_monthly_revenue_ignores_canceled(con):
    mensal = con.sql("SELECT * FROM mart_receita_mensal").df()
    assert len(mensal) == 1
    assert mensal["receita"].iloc[0] == pytest.approx(165.0 + 110.0)


def test_quality_checks_catch_bad_data(con):
    pipeline.run_checks(con)  # dados válidos passam
    con.execute("UPDATE fct_pedidos SET nota = 7 WHERE pedido_id = 'A'")
    with pytest.raises(pipeline.DataQualityError, match="notas entre 1 e 5"):
        pipeline.run_checks(con)
