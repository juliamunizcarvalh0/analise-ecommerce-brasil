-- Itens de pedido com a categoria do produto.
CREATE OR REPLACE TABLE stg_itens AS
SELECT
    i.order_id                                      AS pedido_id,
    i.order_item_id                                 AS item_seq,
    i.product_id                                    AS produto_id,
    i.seller_id                                     AS vendedor_id,
    coalesce(p.product_category_name, 'sem_categoria') AS categoria,
    CAST(i.price AS DOUBLE)                         AS preco,
    CAST(i.freight_value AS DOUBLE)                 AS frete
FROM raw_order_items i
LEFT JOIN raw_products p USING (product_id);
