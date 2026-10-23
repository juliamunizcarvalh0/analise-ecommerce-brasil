-- Um pedido por linha, já com o cliente e as métricas de entrega.
CREATE OR REPLACE TABLE stg_pedidos AS
SELECT
    o.order_id                                            AS pedido_id,
    c.customer_unique_id                                  AS cliente_id,
    upper(c.customer_state)                               AS estado,
    o.order_status                                        AS status,
    CAST(o.order_purchase_timestamp AS TIMESTAMP)         AS comprado_em,
    CAST(date_trunc('month', CAST(o.order_purchase_timestamp AS TIMESTAMP)) AS DATE) AS mes,
    CAST(o.order_delivered_customer_date AS TIMESTAMP)    AS entregue_em,
    CAST(o.order_estimated_delivery_date AS DATE)         AS prazo_estimado,
    date_diff('day', CAST(o.order_purchase_timestamp AS TIMESTAMP),
                     CAST(o.order_delivered_customer_date AS TIMESTAMP)) AS dias_entrega,
    date_diff('day', CAST(o.order_estimated_delivery_date AS DATE),
                     CAST(CAST(o.order_delivered_customer_date AS TIMESTAMP) AS DATE)) AS atraso_dias
FROM raw_orders o
JOIN raw_customers c USING (customer_id);
