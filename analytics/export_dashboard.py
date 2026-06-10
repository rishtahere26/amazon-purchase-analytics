#!/usr/bin/env python3
"""Export the SQLite database to the interactive dashboard.

Reads anonymized records from the DB, packs them into a compact JSON payload,
and injects it into web/template.html. The result is a single self-contained
static HTML file with client-side date filtering. Stdlib only.

Usage:
    python3 analytics/export_dashboard.py --db data/demo.db --out docs/index.html
"""
import argparse, json, sqlite3
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title-note", default="", help="optional note shown in the header")
    args = ap.parse_args()

    con = sqlite3.connect(args.db)
    cats, pays, reasons = [], [], []
    cat_i, pay_i, reason_i = {}, {}, {}

    def idx(v, names, m):
        if v not in m:
            m[v] = len(names)
            names.append(v)
        return m[v]

    items = [[o, d, h, t, idx(c, cats, cat_i), idx(p, pays, pay_i), s]
             for o, d, h, t, c, p, s in con.execute(
                 "SELECT order_key, date, hour, total, category, payment, shipping_charge"
                 " FROM items ORDER BY date")]
    refunds = [[o, a, idx(r, reasons, reason_i)]
               for o, a, r in con.execute("SELECT order_key, amount, reason FROM refunds")]
    con.close()

    data = {
        "meta": {"generated": datetime.now().strftime("%Y-%m-%d"), "timezone": "local",
                 "note": args.title_note},
        "catNames": cats, "payNames": pays, "reasonNames": reasons,
        "items": items, "refunds": refunds, "cancelledDates": [],
    }
    template = (ROOT / "web" / "template.html").read_text()
    html = template.replace("/*__DATA__*/", json.dumps(data, separators=(",", ":")))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html)
    print(f"wrote {out} ({len(html)//1024} KB, {len(items)} items, {len(refunds)} refunds)")

if __name__ == "__main__":
    main()
