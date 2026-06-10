#!/usr/bin/env python3
"""ETL: Amazon 'Your Orders' export (CSV) -> anonymized SQLite database.

- Order IDs are replaced with sequential integers.
- Product names are reduced to a category (regex classifier) and discarded.
- Payment methods are reduced to card networks (all digits stripped).
- Refund records are deduplicated (the export contains retry batches) and
  capped at the order total.

Usage:
    python3 etl/load.py --source <export-dir> --db data/purchases.db
The source directory is searched recursively for 'Order History.csv' and
'Refund Details.csv'. Stdlib only — no dependencies.
"""
import argparse, csv, re, sqlite3, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("America/Detroit")

CATEGORIES = [
 ("Grocery & Food", r"snack|coffee|tea\b|chocolate|candy|spice|masala|rice\b|flour|atta|dal\b|lentil|ghee|paneer|sauce|noodle|pasta|cereal|protein bar|honey|sugar|salt\b|oil\b|ginger|garlic|cashew|almond|nuts|juice|drink|soda|biscuit|cookie|cracker|grocery|food|avocado|fruit|vegetable|chips"),
 ("Health & Personal Care", r"vitamin|supplement|protein powder|creatine|medicin|tylenol|advil|bandage|first aid|thermometer|shampoo|conditioner|soap|body wash|lotion|moisturiz|sunscreen|toothpaste|toothbrush|floss|deodorant|razor|wax\b|serum|skincare|skin care|face mask|hair oil|castor|biotin|collagen|melatonin|probiotic|ashwagandha|pads\b|tampon|menstrual"),
 ("Beauty & Cosmetics", r"makeup|lipstick|lip gloss|mascara|eyeliner|concealer|nail polish|eyeshadow|blush\b|kajal|highlighter|cosmetic|perfume|fragrance|cologne|lash"),
 ("Electronics & Tech", r"laptop|monitor|keyboard|mouse\b|usb|hdmi|charger|charging|cable|adapter|router|webcam|headphone|earbud|airpod|speaker|bluetooth|echo\b|alexa|fire tv|kindle|tablet|ipad|iphone|samsung galaxy|ssd|hard drive|memory card|sd card|power bank|tripod|ring light|smartwatch|fitbit|camera|printer|ink\b|toner"),
 ("Home & Kitchen", r"comforter|bedding|sheet set|pillow|blanket|duvet|mattress|curtain|rug\b|carpet|lamp\b|shelf|shelving|organizer|storage|hanger|laundry|detergent|cleaner|cleaning|mop\b|broom|vacuum|trash|kitchen|cookware|pan\b|pot\b|skillet|knife|cutting board|utensil|spatula|blender|mixer|toaster|kettle|instant pot|air fryer|pressure cooker|tawa|kadai|plate\b|bowl|mug\b|cup\b|glass\b|container|tupperware|jar\b|towel|bathroom|shower|soap dispenser|candle|decor|frame\b|vase|plant\b|humidifier|purifier|heater|fan\b|furniture|desk\b|chair|table\b|sofa|ottoman|drawer"),
 ("Clothing & Accessories", r"shirt|t-shirt|tee\b|dress\b|kurta|saree|sari\b|lehenga|jeans|pant|legging|trouser|short[s]?\b|skirt|jacket|coat\b|hoodie|sweater|sweatshirt|bra\b|underwear|sock|shoe|sneaker|sandal|slipper|boot|heel|scarf|glove|hat\b|cap\b|belt\b|wallet|purse|handbag|backpack|jewelry|necklace|earring|bracelet|ring\b|watch\b|sunglasses|blouse|salwar|dupatta|nightgown|pajama|swimsuit|bikini"),
 ("Baby & Kids", r"baby|infant|toddler|diaper|wipes|pacifier|stroller|crib|onesie|kids\b|children"),
 ("Sports & Fitness", r"yoga|dumbbell|weight[s]?\b|resistance band|treadmill|exercise|fitness|gym\b|workout|bicycle|bike\b|helmet|tennis|badminton|cricket|basketball|football|soccer|golf|hiking|camping|tent\b"),
 ("Books & Media", r"book\b|paperback|hardcover|novel|notebook|journal|planner|pen\b|pencil|marker|stationery|sticky note"),
 ("Pet Supplies", r"\bdog\b|\bcat\b|\bpet\b|puppy|kitten|litter\b|leash"),
 ("Auto & Tools", r"car\b|automotive|tire|wiper|drill|screwdriver|wrench|toolkit|tool set|hammer|tape measure|glue|sealant|paint\b"),
]

def categorize(name: str) -> str:
    n = (name or "").lower()
    for cat, pat in CATEGORIES:
        if re.search(pat, n):
            return cat
    return "Other"

def normalize_payment(s: str) -> str:
    """Strip every digit / card-number fragment; collapse to network names."""
    s = re.sub(r"\s*-\s*\d+", "", s or "")
    s = re.sub(r"\d", "", s).strip()
    s = s.replace("Gift Certificate/Card", "Gift Card")
    parts = sorted(p.strip() for p in s.split(" and ") if p.strip())
    return " + ".join(parts) if parts else "Other"

def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

def parse_ts(s):
    if not s or s == "Not Available":
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(LOCAL_TZ)
    except ValueError:
        return None

def find_csv(root: Path, filename: str) -> Path:
    hits = list(root.rglob(filename))
    if not hits:
        sys.exit(f"error: '{filename}' not found under {root}")
    return hits[0]

def load_csv(path: Path):
    with open(path, encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))

def dedupe_refunds(rows):
    """The export logs the same refund batch repeatedly (system retries).
    Group by (order, refund date) -> creation-timestamp batches -> keep the
    latest batch only."""
    grouped = defaultdict(lambda: defaultdict(list))
    for r in rows:
        grouped[(r["Order ID"], r["Refund Date"])][r["Creation Date"]].append(r)
    out = []
    for batches in grouped.values():
        out.extend(batches[max(batches)])
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True, help="Amazon export directory")
    ap.add_argument("--db", required=True, help="output SQLite path")
    args = ap.parse_args()

    root = Path(args.source)
    orders_rows = load_csv(find_csv(root, "Order History.csv"))
    refund_rows = load_csv(find_csv(root, "Refund Details.csv"))

    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    schema = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"
    con.executescript(schema.read_text())

    # ---- items -------------------------------------------------------------
    oid_map, order_dates = {}, {}
    order_totals = defaultdict(float)
    items = []
    for r in orders_rows:
        if r.get("Order Status") != "Closed":
            continue
        ts = parse_ts(r.get("Order Date"))
        if ts is None:
            continue
        key = oid_map.setdefault(r["Order ID"], len(oid_map))
        date = ts.strftime("%Y-%m-%d")
        if key not in order_dates or date < order_dates[key]:
            order_dates[key] = date
        total = fnum(r.get("Total Amount"))
        order_totals[r["Order ID"]] += total
        items.append((key, ts.isoformat(), date, ts.hour, round(total, 2),
                      int(fnum(r.get("Original Quantity")) or 1),
                      categorize(r.get("Product Name")),
                      normalize_payment(r.get("Payment Method Type")),
                      round(fnum(r.get("Shipping Charge")), 2)))

    con.executemany("INSERT INTO orders(order_key, order_date) VALUES (?,?)",
                    sorted(order_dates.items()))
    con.executemany(
        "INSERT INTO items(order_key, ts, date, hour, total, quantity, category, payment, shipping_charge)"
        " VALUES (?,?,?,?,?,?,?,?,?)", items)

    # ---- refunds -----------------------------------------------------------
    completed = [r for r in refund_rows
                 if r.get("Payment Status") == "Completed"
                 and r.get("Disbursement Type") == "Refund"]
    deduped = dedupe_refunds(completed)
    per_order = defaultdict(float)
    for r in deduped:
        per_order[r["Order ID"]] += fnum(r["Refund Amount"])
    cap = {o: (order_totals[o] / v if o in order_totals and v > order_totals[o] + 0.01 else 1.0)
           for o, v in per_order.items()}
    refunds, skipped = [], 0
    for r in deduped:
        o = r["Order ID"]
        if o not in oid_map:
            skipped += 1
            continue
        rd = parse_ts(r.get("Refund Date")) or parse_ts(r.get("Creation Date"))
        refunds.append((oid_map[o], round(fnum(r["Refund Amount"]) * cap[o], 2),
                        r.get("Reversal Reason") or "Unknown",
                        rd.strftime("%Y-%m-%d") if rd else order_dates[oid_map[o]]))
    con.executemany("INSERT INTO refunds(order_key, amount, reason, refund_date) VALUES (?,?,?,?)",
                    refunds)
    con.commit()

    g = con.execute("SELECT ROUND(SUM(total),2), COUNT(*), COUNT(DISTINCT order_key) FROM items").fetchone()
    rf = con.execute("SELECT ROUND(SUM(amount),2), COUNT(*) FROM refunds").fetchone()
    print(f"loaded {db_path}: {g[1]} items / {g[2]} orders, gross ${g[0]:,.2f}; "
          f"{rf[1]} refunds totalling ${rf[0] or 0:,.2f} ({skipped} skipped, no matching order)")
    con.close()

if __name__ == "__main__":
    main()
