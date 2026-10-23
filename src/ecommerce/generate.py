"""Gera dados sintéticos no MESMO formato do dataset público da Olist.

Assim o pipeline roda sem download, e quem quiser pode trocar pelos dados
reais (https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce): basta
colocar os CSVs originais em ``data/raw/`` com os nomes abaixo.

Padrões embutidos nos dados (que a análise deve conseguir redescobrir):
- entregas para estados longe do Sudeste demoram mais e atrasam mais;
- atraso na entrega derruba a nota da avaliação;
- há sazonalidade (Black Friday em novembro e alta em dezembro).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

RAW_FILES = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "products": "olist_products_dataset.csv",
    "payments": "olist_order_payments_dataset.csv",
    "reviews": "olist_order_reviews_dataset.csv",
}

# estado: (peso na base de clientes, dias médios de entrega saindo de SP)
STATES = {
    "SP": (0.42, 6), "RJ": (0.13, 10), "MG": (0.12, 9), "RS": (0.055, 12),
    "PR": (0.05, 10), "SC": (0.037, 12), "BA": (0.034, 16), "DF": (0.021, 11),
    "GO": (0.02, 13), "ES": (0.02, 13), "PE": (0.017, 18), "CE": (0.013, 19),
    "PA": (0.01, 21), "MT": (0.009, 16), "MA": (0.007, 20), "MS": (0.007, 14),
    "PB": (0.005, 19), "PI": (0.005, 19), "RN": (0.005, 18), "AL": (0.004, 21),
    "SE": (0.003, 20), "TO": (0.003, 17), "RO": (0.002, 19), "AM": (0.0015, 24),
    "AC": (0.001, 23), "AP": (0.0007, 26), "RR": (0.0005, 27),
}
CITY_BY_STATE = {
    "SP": "sao paulo", "RJ": "rio de janeiro", "MG": "belo horizonte", "RS": "porto alegre",
    "PR": "curitiba", "SC": "florianopolis", "BA": "salvador", "DF": "brasilia",
    "GO": "goiania", "ES": "vitoria", "PE": "recife", "CE": "fortaleza", "PA": "belem",
    "MT": "cuiaba", "MA": "sao luis", "MS": "campo grande", "PB": "joao pessoa",
    "PI": "teresina", "RN": "natal", "AL": "maceio", "SE": "aracaju", "TO": "palmas",
    "RO": "porto velho", "AM": "manaus", "AC": "rio branco", "AP": "macapa", "RR": "boa vista",
}
# categoria: (peso, preço médio)
CATEGORIES = {
    "cama_mesa_banho": (0.11, 95), "beleza_saude": (0.10, 130), "esporte_lazer": (0.09, 115),
    "moveis_decoracao": (0.08, 90), "informatica_acessorios": (0.08, 120),
    "utilidades_domesticas": (0.07, 85), "relogios_presentes": (0.06, 200),
    "telefonia": (0.05, 70), "ferramentas_jardim": (0.04, 110), "automotivo": (0.04, 140),
    "brinquedos": (0.04, 115), "cool_stuff": (0.04, 165), "perfumaria": (0.035, 120),
    "bebes": (0.03, 130), "eletronicos": (0.03, 60), "papelaria": (0.025, 90),
    "fashion_bolsas_e_acessorios": (0.025, 75), "pet_shop": (0.02, 110),
    "eletrodomesticos": (0.02, 300), "livros_interesse_geral": (0.015, 85),
    "consoles_games": (0.015, 140), "audio": (0.01, 135),
}
MONTH_WEIGHT = {1: 0.85, 2: 0.8, 3: 0.95, 4: 0.9, 5: 1.0, 6: 0.95,
                7: 1.0, 8: 1.05, 9: 0.95, 10: 1.0, 11: 1.55, 12: 1.25}


def _choice(rng, mapping: dict, size: int):
    keys = list(mapping)
    w = np.array([v[0] if isinstance(v, tuple) else v for v in mapping.values()], dtype=float)
    return rng.choice(keys, size=size, p=w / w.sum())


def generate(n_orders: int = 40_000, seed: int = 42,
             start: str = "2023-01-01", end: str = "2024-12-31") -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    # --- clientes (pessoas) e recompra --------------------------------------
    n_people = int(n_orders * 0.88)
    people = pd.DataFrame({
        "customer_unique_id": [f"u{i:07d}" for i in range(n_people)],
        "customer_state": _choice(rng, STATES, n_people),
    })
    # ~10% das pessoas compram mais de uma vez
    buyer_idx = np.concatenate([
        np.arange(n_people),
        rng.choice(n_people, size=n_orders - n_people, replace=True),
    ])
    rng.shuffle(buyer_idx)

    # --- datas de compra com sazonalidade -----------------------------------
    days = pd.date_range(start, end, freq="D")
    trend = np.linspace(0.8, 1.2, len(days))  # crescimento ao longo do período
    weights = trend * days.month.map(MONTH_WEIGHT).to_numpy()
    bf = (days.month == 11) & (days.day >= 22) & (days.day <= 29)
    weights = np.where(bf, weights * 3.0, weights)
    purchase_day = rng.choice(days, size=n_orders, p=weights / weights.sum())
    purchase_ts = pd.to_datetime(purchase_day) + pd.to_timedelta(
        rng.integers(6 * 3600, 24 * 3600, n_orders), unit="s")

    # Ordena por data para que a "primeira compra" de cada pessoa venha antes.
    order_frame = pd.DataFrame({"person": buyer_idx, "ts": purchase_ts}).sort_values("ts")
    order_frame["order_id"] = [f"o{i:07d}" for i in range(n_orders)]
    order_frame["customer_id"] = [f"c{i:07d}" for i in range(n_orders)]
    state = people["customer_state"].to_numpy()[order_frame["person"].to_numpy()]

    # --- status e logística -------------------------------------------------
    status = rng.choice(["delivered", "shipped", "canceled", "unavailable"],
                        size=n_orders, p=[0.965, 0.02, 0.01, 0.005])
    base_days = np.array([STATES[s][1] for s in state])
    ts = order_frame["ts"].to_numpy()
    approved = ts + pd.to_timedelta(rng.exponential(0.4, n_orders) * 24, unit="h").to_numpy()
    carrier = approved + pd.to_timedelta(rng.gamma(2, 1.3, n_orders), unit="D").to_numpy()
    # O prazo estimado é generoso; o atraso aparece mais nos estados distantes
    # e em novembro/dezembro, quando a logística fica congestionada.
    peak = np.isin(pd.DatetimeIndex(ts).month, [11, 12])
    delivery_days = rng.gamma(4, base_days / 4) * np.where(peak, 1.35, 1.0)
    delivered = ts + pd.to_timedelta(delivery_days, unit="D").to_numpy()
    estimated_raw = ts + pd.to_timedelta(base_days * 1.55 + 4, unit="D").to_numpy()
    estimated = pd.DatetimeIndex(estimated_raw).normalize()

    is_delivered = status == "delivered"

    def _ts(values, mask=None) -> pd.Series:
        s = pd.Series(pd.DatetimeIndex(values).floor("s"))
        return s if mask is None else s.where(mask)

    orders = pd.DataFrame({
        "order_id": order_frame["order_id"].to_numpy(),
        "customer_id": order_frame["customer_id"].to_numpy(),
        "order_status": status,
        "order_purchase_timestamp": _ts(ts),
        "order_approved_at": _ts(approved, status != "canceled"),
        "order_delivered_carrier_date": _ts(carrier, np.isin(status, ["delivered", "shipped"])),
        "order_delivered_customer_date": _ts(delivered, is_delivered),
        "order_estimated_delivery_date": estimated,
    })

    customers = pd.DataFrame({
        "customer_id": orders["customer_id"],
        "customer_unique_id": people["customer_unique_id"].to_numpy()[
            order_frame["person"].to_numpy()
        ],
        "customer_zip_code_prefix": rng.integers(1000, 99999, n_orders),
        "customer_city": [CITY_BY_STATE[s] for s in state],
        "customer_state": state,
    })

    # --- produtos e itens ---------------------------------------------------
    n_products = 3000
    product_cat = _choice(rng, CATEGORIES, n_products)
    category_price = np.array([CATEGORIES[c][1] for c in product_cat])
    product_price = category_price * rng.lognormal(0, 0.45, n_products)
    products = pd.DataFrame({
        "product_id": [f"p{i:05d}" for i in range(n_products)],
        "product_category_name": product_cat,
        "product_weight_g": (rng.lognormal(6.5, 1.0, n_products)).round().astype(int),
    })
    sellers = [f"s{i:04d}" for i in range(600)]

    n_items = rng.choice([1, 2, 3, 4], size=n_orders, p=[0.88, 0.09, 0.02, 0.01])
    item_order = np.repeat(orders["order_id"].to_numpy(), n_items)
    item_seq = np.concatenate([np.arange(1, k + 1) for k in n_items])
    item_product = rng.integers(0, n_products, len(item_order))
    item_state = np.repeat(state, n_items)
    freight_base = np.array([STATES[s][1] for s in item_state]) * 1.3 + 8
    order_items = pd.DataFrame({
        "order_id": item_order,
        "order_item_id": item_seq,
        "product_id": products["product_id"].to_numpy()[item_product],
        "seller_id": rng.choice(sellers, len(item_order)),
        "shipping_limit_date": np.repeat(pd.DatetimeIndex(ts) + pd.Timedelta(days=3), n_items),
        "price": (product_price[item_product] * rng.uniform(0.95, 1.05, len(item_order))).round(2),
        "freight_value": (freight_base * rng.lognormal(0, 0.3, len(item_order))).round(2),
    })

    # --- pagamentos ---------------------------------------------------------
    order_total = order_items.assign(total=lambda d: d.price + d.freight_value) \
        .groupby("order_id", sort=False)["total"].sum().reindex(orders["order_id"]).to_numpy()
    pay_type = rng.choice(["credit_card", "pix", "boleto", "debit_card"],
                          size=n_orders, p=[0.62, 0.20, 0.13, 0.05])
    installments = np.where(
        pay_type == "credit_card",
        np.clip(np.ceil(order_total / rng.uniform(40, 120, n_orders)), 1, 10), 1
    ).astype(int)
    payments = pd.DataFrame({
        "order_id": orders["order_id"],
        "payment_sequential": 1,
        "payment_type": pay_type,
        "payment_installments": installments,
        "payment_value": order_total.round(2),
    })

    # --- avaliações: o atraso é o principal fator da nota -------------------
    delay = (pd.DatetimeIndex(delivered) - estimated).days.to_numpy().astype(float)
    late = is_delivered & (delay > 0)
    mean_score = np.where(~is_delivered, 1.8,
                          np.where(late, 4.25 - 0.22 * np.clip(delay, 0, 12), 4.35))
    score = np.clip(np.round(mean_score + rng.normal(0, 0.9, n_orders)), 1, 5).astype(int)
    has_review = rng.random(n_orders) < 0.97
    review_date = np.where(is_delivered, delivered, ts + np.timedelta64(20, "D"))
    reviews = pd.DataFrame({
        "review_id": [f"r{i:07d}" for i in range(n_orders)],
        "order_id": orders["order_id"],
        "review_score": score,
        "review_creation_date": pd.DatetimeIndex(review_date).normalize()
                                + pd.Timedelta(days=1),
    })[has_review]

    return {"customers": customers, "orders": orders, "order_items": order_items,
            "products": products, "payments": payments, "reviews": reviews}


def write(tables: dict[str, pd.DataFrame], folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    for name, df in tables.items():
        df.to_csv(folder / RAW_FILES[name], index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Gera dados sintéticos no formato Olist")
    parser.add_argument("--orders", type=int, default=40_000)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("data/raw"))
    args = parser.parse_args()
    tables = generate(n_orders=args.orders, seed=args.seed)
    write(tables, args.out)
    for name, df in tables.items():
        print(f"{RAW_FILES[name]:40s} {len(df):>8,} linhas")


if __name__ == "__main__":
    main()
