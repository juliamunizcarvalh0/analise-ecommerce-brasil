-- No dataset original há pedidos com mais de uma avaliação.
-- Mantemos só a mais recente de cada pedido.
CREATE OR REPLACE TABLE stg_avaliacoes AS
SELECT
    order_id                               AS pedido_id,
    CAST(review_score AS INTEGER)          AS nota,
    CAST(review_creation_date AS DATE)     AS avaliado_em
FROM raw_reviews
QUALIFY row_number() OVER (
    PARTITION BY order_id ORDER BY CAST(review_creation_date AS TIMESTAMP) DESC, review_id
) = 1;
