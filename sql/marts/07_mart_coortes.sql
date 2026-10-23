-- Retenção por coorte: dos clientes que compraram pela 1ª vez no mês X,
-- quantos voltaram a comprar N meses depois?
CREATE OR REPLACE TABLE mart_coortes AS
WITH compras AS (
    SELECT DISTINCT cliente_id, mes
    FROM fct_pedidos
    WHERE status NOT IN ('canceled', 'unavailable')
),
primeira AS (
    SELECT cliente_id, min(mes) AS coorte FROM compras GROUP BY cliente_id
),
atividade AS (
    SELECT
        p.coorte,
        date_diff('month', p.coorte, c.mes) AS meses_desde_primeira,
        count(DISTINCT c.cliente_id)        AS clientes_ativos
    FROM compras c
    JOIN primeira p USING (cliente_id)
    GROUP BY 1, 2
)
SELECT
    coorte,
    meses_desde_primeira,
    clientes_ativos,
    round(clientes_ativos / first_value(clientes_ativos) OVER (
        PARTITION BY coorte ORDER BY meses_desde_primeira), 4) AS retencao
FROM atividade
ORDER BY coorte, meses_desde_primeira;
