-- Segmentação RFM (Recência, Frequência, Valor) de cada cliente.
CREATE OR REPLACE TABLE mart_rfm AS
WITH ref AS (
    SELECT max(comprado_em)::DATE + 1 AS data_ref FROM fct_pedidos
),
clientes AS (
    SELECT
        cliente_id,
        date_diff('day', max(comprado_em)::DATE, (SELECT data_ref FROM ref)) AS recencia_dias,
        count(*)                                                            AS frequencia,
        round(sum(valor_total), 2)                                          AS valor
    FROM fct_pedidos
    WHERE status NOT IN ('canceled', 'unavailable')
    GROUP BY cliente_id
),
scores AS (
    SELECT
        *,
        ntile(5) OVER (ORDER BY recencia_dias DESC)                         AS r,
        -- Como a maioria compra só uma vez, a frequência vira faixas fixas.
        CASE WHEN frequencia >= 3 THEN 5 WHEN frequencia = 2 THEN 4 ELSE 1 END AS f,
        ntile(5) OVER (ORDER BY valor)                                      AS m
    FROM clientes
)
SELECT
    *,
    CASE
        WHEN f >= 4 AND r >= 4                 THEN 'campeoes'
        WHEN f >= 4                            THEN 'fieis_em_risco'
        WHEN r >= 4 AND m >= 4                 THEN 'novos_alto_valor'
        WHEN r >= 4                            THEN 'novos'
        WHEN r <= 2 AND m >= 4                 THEN 'alto_valor_dormente'
        ELSE                                        'inativos'
    END AS segmento
FROM scores;
