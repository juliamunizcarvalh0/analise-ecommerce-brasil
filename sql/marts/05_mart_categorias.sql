-- Receita e satisfação por categoria (a categoria do item mais caro do pedido).
CREATE OR REPLACE TABLE mart_categorias AS
SELECT
    categoria_principal                                            AS categoria,
    count(*)                                                       AS pedidos,
    round(sum(valor_total), 2)                                     AS receita,
    round(sum(valor_total) / sum(sum(valor_total)) OVER (), 4)     AS participacao_receita,
    round(avg(valor_total), 2)                                     AS ticket_medio,
    round(avg(nota), 2)                                            AS nota_media
FROM fct_pedidos
WHERE status NOT IN ('canceled', 'unavailable')
GROUP BY categoria_principal
ORDER BY receita DESC;
