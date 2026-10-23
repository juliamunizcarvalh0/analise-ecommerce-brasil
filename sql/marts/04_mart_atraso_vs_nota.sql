-- Quanto o atraso na entrega afeta a satisfação do cliente?
CREATE OR REPLACE TABLE mart_atraso_vs_nota AS
WITH faixas AS (
    SELECT
        CASE
            WHEN atraso_dias <= -7 THEN '1. 7+ dias adiantado'
            WHEN atraso_dias <= 0  THEN '2. no prazo'
            WHEN atraso_dias <= 3  THEN '3. 1 a 3 dias de atraso'
            WHEN atraso_dias <= 7  THEN '4. 4 a 7 dias de atraso'
            ELSE                        '5. mais de 7 dias de atraso'
        END AS faixa_atraso,
        nota
    FROM fct_pedidos
    WHERE status = 'delivered' AND entregue_em IS NOT NULL AND nota IS NOT NULL
)
SELECT
    faixa_atraso,
    count(*)                                              AS pedidos,
    round(avg(nota), 2)                                   AS nota_media,
    round(avg(CASE WHEN nota <= 2 THEN 1 ELSE 0 END), 4)  AS pct_notas_ruins,
    round(avg(CASE WHEN nota = 5 THEN 1 ELSE 0 END), 4)   AS pct_nota_5
FROM faixas
GROUP BY faixa_atraso
ORDER BY faixa_atraso;
