-- Receita, pedidos e ticket médio por mês, com crescimento mês a mês.
-- Considera apenas pedidos que não foram cancelados nem ficaram indisponíveis.
CREATE OR REPLACE TABLE mart_receita_mensal AS
WITH base AS (
    SELECT
        mes,
        count(*)                       AS pedidos,
        count(DISTINCT cliente_id)     AS clientes,
        sum(valor_total)               AS receita,
        avg(valor_total)               AS ticket_medio
    FROM fct_pedidos
    WHERE status NOT IN ('canceled', 'unavailable')
    GROUP BY mes
)
SELECT
    mes,
    pedidos,
    clientes,
    round(receita, 2)                                                   AS receita,
    round(ticket_medio, 2)                                              AS ticket_medio,
    round(receita / lag(receita) OVER (ORDER BY mes) - 1, 4)            AS crescimento_mom,
    round(receita / lag(receita, 12) OVER (ORDER BY mes) - 1, 4)        AS crescimento_yoy
FROM base
ORDER BY mes;
