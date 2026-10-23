-- Tabela fato: um pedido por linha, pronta para análise.
CREATE OR REPLACE TABLE fct_pedidos AS
WITH itens AS (
    SELECT
        pedido_id,
        count(*)                              AS qtd_itens,
        sum(preco)                            AS valor_produtos,
        sum(frete)                            AS valor_frete,
        arg_max(categoria, preco)             AS categoria_principal
    FROM stg_itens
    GROUP BY pedido_id
)
SELECT
    p.*,
    i.qtd_itens,
    round(i.valor_produtos, 2)                       AS valor_produtos,
    round(i.valor_frete, 2)                          AS valor_frete,
    round(i.valor_produtos + i.valor_frete, 2)       AS valor_total,
    i.categoria_principal,
    pg.forma_pagamento,
    pg.parcelas,
    a.nota,
    p.atraso_dias > 0                                AS atrasado
FROM stg_pedidos p
JOIN itens i USING (pedido_id)
LEFT JOIN stg_pagamentos pg USING (pedido_id)
LEFT JOIN stg_avaliacoes a USING (pedido_id);
