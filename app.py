"""Dashboard interativo do e-commerce.

Rodar: streamlit run app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ecommerce import generate, pipeline  # noqa: E402

DB_PATH = ROOT / "data" / "ecommerce.duckdb"
RAW_DIR = ROOT / "data" / "raw"
BLUE, RED = "#2563eb", "#dc2626"

st.set_page_config(page_title="E-commerce Brasil", page_icon="📦", layout="wide")


@st.cache_resource
def get_connection() -> duckdb.DuckDBPyConnection:
    # Na primeira execução (ex.: deploy no Streamlit Cloud) o banco é construído.
    if not DB_PATH.exists():
        if not RAW_DIR.exists():
            generate.write(generate.generate(), RAW_DIR)
        pipeline.run(RAW_DIR, DB_PATH, verbose=False).close()
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data
def query(sql: str, params: tuple = ()) -> pd.DataFrame:
    return get_connection().execute(sql, list(params)).df()


def brl(value: float) -> str:
    return "R$ " + f"{value:,.0f}".replace(",", ".")


st.title("📦 Análise de E-commerce no Brasil")
st.caption("Pipeline SQL em DuckDB sobre dados no formato do dataset público da Olist.")

limits = query("SELECT min(mes) AS ini, max(mes) AS fim FROM fct_pedidos").iloc[0]
estados = query("SELECT DISTINCT estado FROM fct_pedidos ORDER BY estado")["estado"].tolist()

with st.sidebar:
    st.header("Filtros")
    periodo = st.slider(
        "Período",
        min_value=limits["ini"].date(),
        max_value=limits["fim"].date(),
        value=(limits["ini"].date(), limits["fim"].date()),
        format="MM/YYYY",
    )
    sel_estados = st.multiselect("Estados", estados, placeholder="Todos")

filtro = "mes BETWEEN ? AND ? AND status NOT IN ('canceled', 'unavailable')"
params: list = [periodo[0], periodo[1]]
if sel_estados:
    filtro += f" AND estado IN ({','.join('?' * len(sel_estados))})"
    params += sel_estados
params_t = tuple(params)

kpi = query(f"""
    SELECT count(*) AS pedidos, sum(valor_total) AS receita, avg(valor_total) AS ticket,
           avg(nota) AS nota, avg(CASE WHEN status = 'delivered' THEN atrasado::INT END) AS atraso,
           count(DISTINCT cliente_id) AS clientes
    FROM fct_pedidos WHERE {filtro}""", params_t).iloc[0]

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Receita", brl(kpi["receita"] or 0))
c2.metric("Pedidos", f"{int(kpi['pedidos']):,}".replace(",", "."))
c3.metric("Ticket médio", brl(kpi["ticket"] or 0))
c4.metric("Nota média", f"{(kpi['nota'] or 0):.2f} ★")
c5.metric("Entregas atrasadas", f"{(kpi['atraso'] or 0):.1%}")

tab1, tab2, tab3, tab4 = st.tabs(["Vendas", "Logística e satisfação", "Clientes", "Categorias"])

with tab1:
    mensal = query(f"""
        SELECT mes, sum(valor_total) AS receita, count(*) AS pedidos
        FROM fct_pedidos WHERE {filtro} GROUP BY mes ORDER BY mes""", params_t)
    fig = px.bar(mensal, x="mes", y="receita", labels={"mes": "", "receita": "Receita (R$)"},
                 color_discrete_sequence=[BLUE], title="Receita mensal")
    st.plotly_chart(fig, width="stretch")
    pag = query(f"""
        SELECT forma_pagamento, count(*) AS pedidos, avg(valor_total) AS ticket
        FROM fct_pedidos WHERE {filtro} GROUP BY 1 ORDER BY 2 DESC""", params_t)
    st.plotly_chart(
        px.bar(pag, x="forma_pagamento", y="pedidos", color_discrete_sequence=[BLUE],
               labels={"forma_pagamento": "Forma de pagamento", "pedidos": "Pedidos"},
               title="Pedidos por forma de pagamento"),
        width="stretch",
    )

with tab2:
    left, right = st.columns(2)
    atraso = query("SELECT * FROM mart_atraso_vs_nota")
    atraso["faixa"] = atraso["faixa_atraso"].str[3:]
    left.plotly_chart(
        px.bar(atraso, x="faixa", y="nota_media", range_y=[0, 5], text_auto=".2f",
               color="nota_media", color_continuous_scale=[RED, BLUE],
               labels={"faixa": "", "nota_media": "Nota média"},
               title="Nota média por faixa de atraso (todo o período)"),
        width="stretch",
    )
    uf = query(f"""
        SELECT estado, count(*) AS pedidos, avg(dias_entrega) AS dias_entrega,
               avg(atrasado::INT) AS taxa_atraso, avg(nota) AS nota_media
        FROM fct_pedidos WHERE {filtro} AND status = 'delivered'
        GROUP BY estado HAVING count(*) >= 20 ORDER BY dias_entrega DESC""", params_t)
    right.plotly_chart(
        px.scatter(uf, x="dias_entrega", y="nota_media", size="pedidos", text="estado",
                   color="taxa_atraso", color_continuous_scale=[BLUE, RED],
                   labels={"dias_entrega": "Dias médios de entrega", "nota_media": "Nota média",
                           "taxa_atraso": "Taxa de atraso"},
                   title="Estados: prazo de entrega × satisfação"),
        width="stretch",
    )
    st.dataframe(uf.style.format({"dias_entrega": "{:.1f}", "taxa_atraso": "{:.1%}",
                                  "nota_media": "{:.2f}"}),
                 width="stretch", hide_index=True)

with tab3:
    rfm = query("""
        SELECT segmento, count(*) AS clientes, sum(valor) AS receita, avg(valor) AS valor_medio
        FROM mart_rfm GROUP BY 1 ORDER BY receita DESC""")
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(rfm, x="segmento", y="clientes", color_discrete_sequence=[BLUE],
               title="Clientes por segmento RFM"),
        width="stretch",
    )
    right.plotly_chart(
        px.pie(rfm, names="segmento", values="receita", hole=0.5,
               title="Participação na receita por segmento"),
        width="stretch",
    )
    coortes = query("""
        SELECT strftime(coorte, '%Y-%m') AS coorte, meses_desde_primeira, retencao
        FROM mart_coortes WHERE meses_desde_primeira BETWEEN 1 AND 12""")
    heat = coortes.pivot(index="coorte", columns="meses_desde_primeira", values="retencao")
    st.plotly_chart(
        px.imshow(heat, color_continuous_scale="Blues", aspect="auto", text_auto=".1%",
                  labels={"x": "Meses após a 1ª compra", "y": "Coorte", "color": "Retenção"},
                  title="Retenção por coorte (recompra)"),
        width="stretch",
    )

with tab4:
    cat = query(f"""
        SELECT categoria_principal AS categoria, sum(valor_total) AS receita,
               count(*) AS pedidos, avg(nota) AS nota_media
        FROM fct_pedidos WHERE {filtro} GROUP BY 1 ORDER BY receita DESC""", params_t)
    st.plotly_chart(
        px.bar(cat.head(15).sort_values("receita"), x="receita", y="categoria", orientation="h",
               color_discrete_sequence=[BLUE], title="Top 15 categorias por receita",
               labels={"receita": "Receita (R$)", "categoria": ""}),
        width="stretch",
    )
