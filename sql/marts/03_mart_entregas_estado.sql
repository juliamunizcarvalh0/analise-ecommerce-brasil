-- Desempenho logístico por estado (só pedidos entregues).
CREATE OR REPLACE TABLE mart_entregas_estado AS
SELECT
    estado,
    count(*)                                              AS pedidos_entregues,
    round(avg(dias_entrega), 1)                           AS dias_entrega_medio,
    round(quantile_cont(dias_entrega, 0.9), 1)            AS dias_entrega_p90,
    round(avg(CAST(atrasado AS INTEGER)), 4)              AS taxa_atraso,
    round(avg(valor_frete), 2)                            AS frete_medio,
    round(sum(valor_frete) / sum(valor_total), 4)         AS frete_pct_valor,
    round(avg(nota), 2)                                   AS nota_media
FROM fct_pedidos
WHERE status = 'delivered' AND entregue_em IS NOT NULL
GROUP BY estado
ORDER BY pedidos_entregues DESC;
