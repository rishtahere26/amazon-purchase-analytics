#!/usr/bin/env python3
"""Run every named query in sql/analytics.sql against a database and print
the results as plain-text tables. Stdlib only.

Usage:
    python3 analytics/report.py --db data/demo.db [--query totals]
"""
import argparse, re, sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def parse_queries(sql_text):
    out, name, buf = {}, None, []
    for line in sql_text.splitlines():
        m = re.match(r"--\s*name:\s*(\w+)", line)
        if m:
            if name:
                out[name] = "\n".join(buf).strip()
            name, buf = m.group(1), []
        elif name is not None:
            buf.append(line)
    if name:
        out[name] = "\n".join(buf).strip()
    return out

def print_table(headers, rows):
    widths = [max(len(str(h)), *(len(str(r[i])) for r in rows)) if rows else len(str(h))
              for i, h in enumerate(headers)]
    line = "  ".join(str(h).ljust(w) for h, w in zip(headers, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        print("  ".join(str(v).ljust(w) for v, w in zip(r, widths)))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--query", help="run a single named query")
    args = ap.parse_args()

    queries = parse_queries((ROOT / "sql" / "analytics.sql").read_text())
    con = sqlite3.connect(args.db)
    names = [args.query] if args.query else list(queries)
    for n in names:
        if n not in queries:
            raise SystemExit(f"unknown query '{n}'. available: {', '.join(queries)}")
        cur = con.execute(queries[n])
        print(f"\n== {n} " + "=" * max(0, 58 - len(n)))
        print_table([d[0] for d in cur.description], cur.fetchall())
    con.close()

if __name__ == "__main__":
    main()
