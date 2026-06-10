-- Amazon Purchase Analytics — named analytics queries
-- Each query is delimited by a "-- name:" header so tooling (analytics/report.py)
-- can run them individually.

-- name: totals
SELECT ROUND(SUM(i.total), 2)                                   AS gross_spend,
       (SELECT ROUND(SUM(amount), 2) FROM refunds)              AS refunded,
       ROUND(SUM(i.total) - (SELECT SUM(amount) FROM refunds), 2) AS net_spend,
       COUNT(DISTINCT i.order_key)                              AS orders,
       COUNT(*)                                                 AS items,
       ROUND(SUM(i.total) / COUNT(DISTINCT i.order_key), 2)     AS avg_order_value,
       ROUND(100.0 * (SELECT SUM(amount) FROM refunds) / SUM(i.total), 1) AS refund_rate_pct
FROM items i;

-- name: yearly_spend_vs_refund
SELECT substr(o.order_date, 1, 4)       AS year,
       ROUND(SUM(t.order_total), 2)     AS spend,
       ROUND(SUM(t.refunded), 2)        AS refunded,
       COUNT(*)                         AS orders
FROM v_order_totals t
JOIN orders o USING (order_key)
GROUP BY year ORDER BY year;

-- name: monthly_spend
SELECT * FROM v_monthly;

-- name: category_spend
SELECT category,
       ROUND(SUM(total), 2) AS spend,
       COUNT(*)             AS items,
       ROUND(AVG(total), 2) AS avg_item
FROM items
GROUP BY category
ORDER BY spend DESC;

-- name: day_of_week
SELECT CASE strftime('%w', date)
         WHEN '0' THEN 'Sun' WHEN '1' THEN 'Mon' WHEN '2' THEN 'Tue'
         WHEN '3' THEN 'Wed' WHEN '4' THEN 'Thu' WHEN '5' THEN 'Fri'
         ELSE 'Sat' END     AS weekday,
       ROUND(SUM(total), 2) AS spend,
       COUNT(*)             AS items
FROM items
GROUP BY strftime('%w', date)
ORDER BY strftime('%w', date);

-- name: hourly_items
SELECT hour, COUNT(*) AS items, ROUND(SUM(total), 2) AS spend
FROM items GROUP BY hour ORDER BY hour;

-- name: late_night_share
SELECT ROUND(100.0 * SUM(CASE WHEN hour >= 22 OR hour < 4 THEN 1 ELSE 0 END) / COUNT(*), 1)
       AS late_night_pct
FROM items;

-- name: refund_reasons
SELECT reason, COUNT(*) AS refunds, ROUND(SUM(amount), 2) AS amount
FROM refunds GROUP BY reason ORDER BY refunds DESC;

-- name: payment_mix
SELECT payment, COUNT(*) AS items, ROUND(SUM(total), 2) AS spend
FROM items GROUP BY payment ORDER BY items DESC;

-- name: price_bands
SELECT CASE
         WHEN total < 10  THEN '<$10'
         WHEN total < 25  THEN '$10-25'
         WHEN total < 50  THEN '$25-50'
         WHEN total < 100 THEN '$50-100'
         WHEN total < 250 THEN '$100-250'
         ELSE '$250+' END AS band,
       COUNT(*) AS items
FROM items
GROUP BY band
ORDER BY MIN(total);

-- name: top_spend_days
SELECT date, ROUND(SUM(total), 2) AS spend, COUNT(*) AS items
FROM items GROUP BY date ORDER BY spend DESC LIMIT 10;

-- name: refund_rate_by_category
SELECT i.category,
       ROUND(SUM(i.total), 2)  AS spend,
       ROUND(COALESCE(SUM(r.refunded_share), 0), 2) AS refunded_est,
       ROUND(100.0 * COALESCE(SUM(r.refunded_share), 0) / SUM(i.total), 1) AS refund_pct_est
FROM items i
LEFT JOIN (
    -- distribute an order's refund across its items proportionally to item value
    SELECT i2.item_id,
           rf.refunded * i2.total / t.order_total AS refunded_share
    FROM items i2
    JOIN v_order_totals t USING (order_key)
    JOIN (SELECT order_key, SUM(amount) AS refunded FROM refunds GROUP BY order_key) rf
         USING (order_key)
) r USING (item_id)
GROUP BY i.category
ORDER BY refund_pct_est DESC;
