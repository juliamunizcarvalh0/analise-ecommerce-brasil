-- Um pedido pode ter vários pagamentos (ex.: cartão + voucher).
-- Agregamos por pedido e guardamos a forma de pagamento principal.
CREATE OR REPLACE TABLE stg_pagamentos AS
SELECT
    order_id                                                   AS pedido_id,
    sum(CAST(payment_value AS DOUBLE))                         AS valor_pago,
    arg_max(payment_type, CAST(payment_value AS DOUBLE))       AS forma_pagamento,
    max(CAST(payment_installments AS INTEGER))                 AS parcelas
FROM raw_payments
GROUP BY order_id;
