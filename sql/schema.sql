-- Amazon Purchase Analytics — SQLite schema
-- All identifiers are anonymized at load time: order keys are sequential
-- integers, product names are reduced to categories, payment methods to
-- card networks. No PII enters this database's exported artifacts.

PRAGMA foreign_keys = ON;

DROP TABLE IF EXISTS refunds;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS orders;

CREATE TABLE orders (
    order_key      INTEGER PRIMARY KEY,          -- anonymized sequential id
    order_date     TEXT NOT NULL                 -- date of earliest item (YYYY-MM-DD)
);

CREATE TABLE items (
    item_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_key      INTEGER NOT NULL REFERENCES orders(order_key),
    ts             TEXT NOT NULL,                -- local ISO timestamp
    date           TEXT NOT NULL,                -- YYYY-MM-DD (local)
    hour           INTEGER NOT NULL CHECK (hour BETWEEN 0 AND 23),
    total          REAL NOT NULL,                -- item total incl. tax
    quantity       INTEGER NOT NULL DEFAULT 1,
    category       TEXT NOT NULL,
    payment        TEXT NOT NULL,                -- card network only, no digits
    shipping_charge REAL NOT NULL DEFAULT 0
);

CREATE TABLE refunds (
    refund_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    order_key      INTEGER NOT NULL REFERENCES orders(order_key),
    amount         REAL NOT NULL,                -- deduplicated & capped at order total
    reason         TEXT NOT NULL,
    refund_date    TEXT NOT NULL                 -- YYYY-MM-DD
);

CREATE INDEX idx_items_date     ON items(date);
CREATE INDEX idx_items_order    ON items(order_key);
CREATE INDEX idx_items_category ON items(category);
CREATE INDEX idx_refunds_order  ON refunds(order_key);

-- Convenience views ---------------------------------------------------------

DROP VIEW IF EXISTS v_order_totals;
CREATE VIEW v_order_totals AS
SELECT o.order_key,
       o.order_date,
       SUM(i.total)                 AS order_total,
       COUNT(*)                     AS n_items,
       COALESCE(r.refunded, 0)      AS refunded
FROM orders o
JOIN items i USING (order_key)
LEFT JOIN (SELECT order_key, SUM(amount) AS refunded FROM refunds GROUP BY order_key) r
       USING (order_key)
GROUP BY o.order_key;

DROP VIEW IF EXISTS v_monthly;
CREATE VIEW v_monthly AS
SELECT substr(date, 1, 7)           AS month,
       ROUND(SUM(total), 2)         AS spend,
       COUNT(DISTINCT order_key)    AS orders,
       COUNT(*)                     AS items
FROM items
GROUP BY month
ORDER BY month;
