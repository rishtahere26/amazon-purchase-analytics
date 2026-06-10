# 📦 Amazon Purchase Analytics

An end-to-end data pipeline that turns a raw Amazon "Your Orders" export into a SQLite analytics database and an interactive, date-filterable spending dashboard — **without exposing any personal data**.

**Live demo (synthetic data):** https://rishtahere26.github.io/amazon-purchase-analytics/

```
Amazon export CSVs ──► etl/load.py ──► SQLite ──► sql/analytics.sql ──► CLI report
   (data/raw/)         anonymize        (db)                │
                       dedupe                               └──► analytics/export_dashboard.py
                       categorize                                      │
                                                            single-file dashboard (Chart.js)
                                                            with client-side date filtering
```

## Privacy by design

The repo and the published dashboard contain **zero personal data**:

- Order IDs are replaced with sequential integers at load time.
- Product names are reduced to a category by a regex classifier, then discarded.
- Payment methods are stripped to card networks — every digit removed.
- Names, addresses, ASINs, and tracking numbers are never read into the database.
- `data/raw/` (your real export), `data/real.db`, and `local/` are gitignored; the committed demo dashboard is built **entirely from synthetic data** (`etl/generate_sample_data.py`).

## Data-quality handling (the interesting part)

Amazon's export has real-world quirks the ETL deals with:

- **Duplicated refund batches** — the export logs the same refund repeatedly (system retries seconds apart). Naively summing refunds overstated them by ~58%. The loader groups by (order, refund date), keeps only the latest creation batch, and caps per-order refunds at the order total.
- **Cancelled orders** mixed into order history; line-item vs order-level amounts; UTC timestamps converted to local time so "late-night shopping" metrics mean something.

## Quick start

```bash
make demo          # synthetic export -> data/demo.db -> docs/index.html
make report-demo   # SQL analytics in your terminal
open docs/index.html
```

With your own data: request your export at amazon.com → Account → "Request your data", unzip into `data/raw/`, then:

```bash
make real          # -> data/real.db + local/index.html (both gitignored)
make report-real
```

## What the dashboard shows

KPIs (gross/net spend, refund rate, AOV), monthly trend, yearly spend vs refunds, category breakdown and mix over time, price-band distribution, day-of-week / hour-of-day rhythm, refund reasons, payment mix, and auto-generated behavioral insights — all recomputed client-side for any date range (presets + custom from/to).

## Stack

Python (stdlib only — no dependencies), SQLite, vanilla JS + Chart.js. One static HTML artifact; no backend, hosts on GitHub Pages.

## Repository layout

```
etl/        generate_sample_data.py, load.py
sql/        schema.sql (tables, views), analytics.sql (named queries)
analytics/  report.py (CLI), export_dashboard.py (HTML build)
web/        template.html (dashboard shell)
docs/       index.html — published demo (synthetic data only)
```
