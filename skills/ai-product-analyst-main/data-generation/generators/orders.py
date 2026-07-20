from __future__ import annotations

"""Generate orders and order_items tables from purchase_complete events.

Each purchase_complete event in the events table becomes one order.
Each order gets 1-4 line items (order_items) with products selected
from the products table.  Promos are applied if the order date falls
within a promotion window.
"""

import numpy as np
import pandas as pd


def generate(
    config: dict,
    events_df: pd.DataFrame,
    products_df: pd.DataFrame,
    users_df: pd.DataFrame,
    promotions_df: pd.DataFrame,
    memberships_df: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config["orders"]
    items_mean = cfg["items_per_order"]["mean"]
    items_min = cfg["items_per_order"]["min"]
    items_max = cfg["items_per_order"]["max"]
    status_dist = cfg["status_distribution"]
    shipping_non_plus = cfg["shipping_non_plus"]

    statuses = list(status_dist.keys())
    status_probs = list(status_dist.values())

    # Get purchase_complete events
    purchases = events_df[events_df["event_type"] == "purchase_complete"].copy()
    purchases = purchases.sort_values("event_timestamp").reset_index(drop=True)
    n_orders = len(purchases)

    if n_orders == 0:
        print("  WARNING: No purchase_complete events found!")
        return pd.DataFrame(), pd.DataFrame()

    # Build a set of plus member user_ids at any given time
    # Simplified: check if user has any active membership
    plus_users = set()
    if memberships_df is not None and len(memberships_df) > 0:
        active = memberships_df[memberships_df["status"].isin(["active", "converted"])]
        plus_users = set(active["user_id"].unique())

    # Build promo lookup: date → (promo_id, discount_pct, target)
    promo_lookup = []
    for _, p in promotions_df.iterrows():
        promo_lookup.append({
            "promo_id": p["promo_id"],
            "start": p["start_date"],
            "end": p["end_date"],
            "discount": p["discount_pct"],
            "target": p["target_segment"],
        })

    # User signup dates for "new_users" promo targeting (within 30 days)
    user_signup = dict(zip(users_df["user_id"], pd.to_datetime(users_df["signup_date"])))

    # Product price lookup
    product_prices = dict(zip(products_df["product_id"], products_df["price"]))
    product_ids = products_df["product_id"].values

    order_rows = []
    item_rows = []
    order_item_counter = 0

    for i in range(n_orders):
        order_id = i + 1
        row = purchases.iloc[i]
        user_id = row["user_id"]
        order_ts = row["event_timestamp"]
        order_date = row["event_date"]
        device = row["device"]
        session_id = row["session_id"]

        is_plus = user_id in plus_users

        # Number of items
        n_items = int(rng.normal(items_mean, 0.8))
        n_items = max(items_min, min(items_max, n_items))

        # Select products for this order
        # If the event has a product_id, include it
        order_products = []
        if pd.notna(row.get("product_id")):
            order_products.append(int(row["product_id"]))
        while len(order_products) < n_items:
            pid = int(rng.choice(product_ids))
            order_products.append(pid)

        # Check for applicable promo
        applied_promo_id = None
        discount_pct = 0.0
        od = order_date if not isinstance(order_date, str) else pd.Timestamp(order_date).date()
        for pr in promo_lookup:
            pr_start = pr["start"] if not isinstance(pr["start"], str) else pd.Timestamp(pr["start"]).date()
            pr_end = pr["end"] if not isinstance(pr["end"], str) else pd.Timestamp(pr["end"]).date()
            if pr_start <= od <= pr_end:
                # Check targeting
                if pr["target"] == "all":
                    applied_promo_id = pr["promo_id"]
                    discount_pct = pr["discount"]
                    break
                elif pr["target"] == "plus_members" and is_plus:
                    applied_promo_id = pr["promo_id"]
                    discount_pct = pr["discount"]
                    break
                elif pr["target"] == "new_users":
                    signup_dt = user_signup.get(user_id)
                    if signup_dt and (pd.Timestamp(od) - signup_dt).days <= 30:
                        applied_promo_id = pr["promo_id"]
                        discount_pct = pr["discount"]
                        break

        # Build order items
        subtotal = 0.0
        total_discount = 0.0
        for pid in order_products:
            order_item_counter += 1
            qty = int(rng.choice([1, 1, 1, 2], p=[0.7, 0.1, 0.1, 0.1]))
            unit_price = product_prices.get(pid, 29.99)
            line_discount = round(unit_price * qty * discount_pct, 2)
            line_total = round(unit_price * qty - line_discount, 2)

            item_rows.append({
                "order_item_id": order_item_counter,
                "order_id": order_id,
                "product_id": pid,
                "quantity": qty,
                "unit_price": unit_price,
                "discount_amount": line_discount,
                "line_total": line_total,
            })
            subtotal += unit_price * qty
            total_discount += line_discount

        subtotal = round(subtotal, 2)
        total_discount = round(total_discount, 2)
        shipping = 0.0 if is_plus else shipping_non_plus
        total_amount = round(subtotal - total_discount + shipping, 2)

        # Order status
        status = rng.choice(statuses, p=status_probs)

        order_rows.append({
            "order_id": order_id,
            "user_id": user_id,
            "order_timestamp": order_ts,
            "order_date": order_date,
            "subtotal": subtotal,
            "discount_amount": total_discount,
            "shipping_amount": shipping,
            "total_amount": total_amount,
            "status": status,
            "promo_id": applied_promo_id,
            "is_plus_member_order": is_plus,
            "device": device,
            "session_id": session_id,
        })

    orders_df = pd.DataFrame(order_rows)
    order_items_df = pd.DataFrame(item_rows)

    print(f"  Generated {len(orders_df):,} orders with {len(order_items_df):,} line items")
    return orders_df, order_items_df
