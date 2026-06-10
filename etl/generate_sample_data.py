#!/usr/bin/env python3
"""Generate a realistic synthetic Amazon 'Your Orders' export for demo purposes.

Produces 'Order History.csv' and 'Refund Details.csv' in data/sample/ with the
same column layout the real export uses, including the quirks the ETL has to
handle (duplicated refund retry batches, cancelled orders, combined payment
methods). Fully deterministic via --seed. Stdlib only.
"""
import argparse, csv, random
from datetime import datetime, timedelta
from pathlib import Path

PRODUCTS = {
 "Electronics & Tech": [
    ("Wireless Bluetooth Headphones with Noise Cancelling", 25, 120),
    ("USB-C Fast Charging Cable 6ft 3-Pack", 8, 18),
    ("1080p HD Webcam with Microphone", 20, 60),
    ("Portable Power Bank 20000mAh", 18, 45),
    ("Mechanical Keyboard RGB Backlit", 35, 110),
    ("4K HDMI Cable 10ft", 9, 20),
    ("Smart Watch Fitness Tracker", 30, 180),
    ("Laptop Stand Adjustable Aluminum", 22, 55)],
 "Home & Kitchen": [
    ("Air Fryer 5.8 Quart Digital Touchscreen", 60, 130),
    ("Memory Foam Pillow Queen Size 2-Pack", 25, 60),
    ("Stainless Steel Cookware Pan Set", 45, 160),
    ("Storage Organizer Bins with Lids 6-Pack", 20, 45),
    ("Blackout Curtains 2 Panels 84 Inch", 22, 50),
    ("Electric Kettle 1.7L Stainless Steel", 25, 55),
    ("Comforter Set Queen 7 Pieces", 55, 140),
    ("LED Desk Lamp with USB Charging Port", 18, 40)],
 "Clothing & Accessories": [
    ("Women's Casual Long Sleeve Shirt", 15, 35),
    ("Men's Running Shoes Lightweight Sneakers", 35, 85),
    ("Crossbody Bag for Women", 20, 55),
    ("Winter Jacket Water Resistant", 45, 120),
    ("Yoga Leggings High Waisted", 18, 38),
    ("Cotton Socks 8-Pack", 12, 24)],
 "Grocery & Food": [
    ("Organic Coffee Beans Medium Roast 2lb", 14, 28),
    ("Protein Bar Variety Pack 18 Count", 18, 32),
    ("Basmati Rice 10lb Bag", 15, 28),
    ("Mixed Nuts Unsalted 2.5lb", 16, 28),
    ("Green Tea Bags 100 Count", 10, 20)],
 "Health & Personal Care": [
    ("Vitamin D3 5000 IU Softgels 360 Count", 12, 25),
    ("Electric Toothbrush with 4 Brush Heads", 25, 70),
    ("Shampoo and Conditioner Set Sulfate Free", 18, 38),
    ("Facial Moisturizer with SPF 30", 14, 30)],
 "Beauty & Cosmetics": [
    ("Liquid Eyeliner Waterproof Black", 8, 16),
    ("Matte Lipstick Set 6 Colors", 12, 25),
    ("Makeup Brush Set 16 Pieces", 12, 30)],
 "Sports & Fitness": [
    ("Resistance Bands Set with Handles", 15, 35),
    ("Yoga Mat Non-Slip 6mm", 18, 40),
    ("Adjustable Dumbbell Set 40lb", 60, 150)],
 "Books & Media": [
    ("Daily Planner Undated with Stickers", 10, 25),
    ("Gel Pens Fine Point 24-Pack", 8, 18)],
}
PAYMENTS = ["Discover - 4242", "Visa - 1111", "AmericanExpress - 9999",
            "Discover - 4242 and Gift Certificate/Card", "Gift Certificate/Card"]
PAYMENT_W = [45, 25, 18, 8, 4]
REFUND_REASONS = ["Customer return", "Order cancelled", "Goodwill refund",
                  "Item damaged in transit", "Price adjustment"]
REASON_W = [70, 12, 8, 7, 3]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/sample")
    ap.add_argument("--seed", type=int, default=26)
    ap.add_argument("--orders", type=int, default=700)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    start = datetime(2023, 1, 1)
    span_days = 900
    cats = list(PRODUCTS)
    cat_w = [len(PRODUCTS[c]) for c in cats]

    order_rows, refund_rows = [], []
    for n in range(args.orders):
        # seasonality: November/December and July (Prime Day-ish) busier
        while True:
            day = rng.randrange(span_days)
            d = start + timedelta(days=day)
            boost = 2.2 if d.month in (11, 12) else (1.6 if d.month == 7 else 1.0)
            if rng.random() < boost / 2.2:
                break
        # late-night bias
        hour = rng.choices(range(24), weights=[3,2,1,1,1,1,2,3,4,5,5,5,5,5,5,5,6,6,7,8,9,10,9,6])[0]
        ts = d.replace(hour=hour, minute=rng.randrange(60), second=rng.randrange(60))
        order_id = f"100-{rng.randrange(10**7):07d}-{rng.randrange(10**7):07d}"
        status = "Cancelled" if rng.random() < 0.05 else "Closed"
        payment = rng.choices(PAYMENTS, weights=PAYMENT_W)[0]
        n_items = rng.choices([1, 2, 3, 4], weights=[62, 22, 11, 5])[0]
        order_total = 0.0
        item_rows = []
        for _ in range(n_items):
            cat = rng.choices(cats, weights=cat_w)[0]
            name, lo, hi = rng.choice(PRODUCTS[cat])
            price = round(rng.uniform(lo, hi), 2)
            tax = round(price * 0.06, 2)
            total = round(price + tax, 2)
            order_total += total
            item_rows.append({
                "ASIN": "B0" + "".join(rng.choices("0123456789ABCDEFGH", k=8)),
                "Currency": "USD",
                "Order Date": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "Order ID": order_id,
                "Order Status": status,
                "Original Quantity": 1,
                "Payment Method Type": payment,
                "Product Name": name,
                "Shipment Item Subtotal": price,
                "Shipment Item Subtotal Tax": tax,
                "Shipping Charge": 0,
                "Total Amount": total,
                "Unit Price": price,
                "Website": "Amazon.com",
            })
        order_rows.extend(item_rows)

        # ~35% of closed orders get refunded (fully or partially)
        if status == "Closed" and rng.random() < 0.35:
            refund_share = rng.choice([1.0, 1.0, 0.5])
            refundable = [r for r in item_rows]
            k = max(1, int(len(refundable) * refund_share))
            chosen = rng.sample(refundable, k)
            ref_date = ts + timedelta(days=rng.randrange(3, 30))
            reason = rng.choices(REFUND_REASONS, weights=REASON_W)[0]
            # simulate the export quirk: the same batch logged 1-4 times
            for retry in range(rng.choices([1, 1, 1, 2, 3, 4], weights=[55, 15, 10, 10, 6, 4])[0]):
                creation = ref_date - timedelta(seconds=rng.randrange(30, 600) * (retry + 1))
                for it in chosen:
                    refund_rows.append({
                        "Creation Date": creation.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "Currency": "USD",
                        "Disbursement Type": "Refund",
                        "Order ID": order_id,
                        "Payment Status": "Completed",
                        "Quantity": 1,
                        "Refund Amount": it["Total Amount"],
                        "Refund Date": ref_date.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                        "Reversal Reason": reason,
                        "Reversal Status": "Completed",
                        "Website": "Amazon.com",
                    })

    with open(out / "Order History.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(order_rows[0]))
        w.writeheader(); w.writerows(order_rows)
    with open(out / "Refund Details.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(refund_rows[0]))
        w.writeheader(); w.writerows(refund_rows)
    print(f"wrote {len(order_rows)} order lines and {len(refund_rows)} refund lines to {out}/")

if __name__ == "__main__":
    main()
