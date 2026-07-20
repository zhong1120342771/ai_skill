from __future__ import annotations

"""Story 5: Checkout Redesign + Promo Confound.

Adjusts mobile checkout conversion rates around Nov 20 (redesign) and
during Black Friday (Nov 25 - Dec 1).  Desktop serves as natural control.

Target conversion rates:
  - Pre-redesign (Nov 1-19): mobile 6.0%, desktop 10.0%
  - Redesign only (Nov 20-24): mobile 6.5%, desktop 10.0%
  - Redesign + promo (Nov 25-30): mobile 9.5%, desktop 13.0%
  - Post-promo (Dec 2-14): mobile 6.5%, desktop 10.0%

The events generator already applies a mobile checkout penalty, so the
baseline gap should exist.  This script fine-tunes the promo period by
injecting additional purchase_complete events during Black Friday for
both mobile and desktop to simulate the promo lift.
"""

import numpy as np
import pandas as pd
from datetime import timedelta


def inject(
    events_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    products_df: pd.DataFrame,
    config: dict,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    cfg = config["stories"]["checkout_confound"]
    promo_start = pd.Timestamp(cfg["promo_start"])
    promo_end = pd.Timestamp(cfg["promo_end"])
    promo_lift_pp = cfg["promo_effect_pp"]

    # During Black Friday promo period, we want to boost checkout conversion
    # by ~3 percentage points for ALL devices (mobile and desktop).
    # This means converting some checkout_started events that don't have
    # corresponding purchase_complete events into completed purchases.

    promo_events = events_df[
        (pd.to_datetime(events_df["event_date"]) >= promo_start) &
        (pd.to_datetime(events_df["event_date"]) <= promo_end)
    ]

    # Find sessions with checkout_started but no purchase_complete
    checkout_sessions = promo_events[
        promo_events["event_type"] == "checkout_started"
    ]["session_id"].unique()

    purchase_sessions = promo_events[
        promo_events["event_type"] == "purchase_complete"
    ]["session_id"].unique()

    abandoned_sessions = set(checkout_sessions) - set(purchase_sessions)

    # Convert some abandoned checkouts to purchases (proportional to promo lift)
    # Current checkout CVR is roughly payment_to_purchase * checkout_to_payment
    # We want to add ~3pp, so convert ~30% of abandoned sessions
    # (This is approximate; the exact number needed depends on baseline)
    conversion_target = 0.30  # Convert 30% of abandoned to simulate promo lift

    sessions_to_convert = rng.choice(
        list(abandoned_sessions),
        size=int(len(abandoned_sessions) * conversion_target),
        replace=False
    ) if len(abandoned_sessions) > 0 else []

    max_event_id = events_df["event_id"].max()
    max_order_id = orders_df["order_id"].max()
    max_item_id = order_items_df["order_item_id"].max()

    new_events = []
    new_orders = []
    new_items = []

    for sid in sessions_to_convert:
        # Get the checkout event for this session
        checkout_evt = promo_events[
            (promo_events["session_id"] == sid) &
            (promo_events["event_type"] == "checkout_started")
        ].iloc[0]

        user_id = checkout_evt["user_id"]
        device = checkout_evt["device"]
        checkout_ts = pd.Timestamp(checkout_evt["event_timestamp"])

        # Add payment_attempted and purchase_complete
        max_event_id += 1
        payment_ts = checkout_ts + timedelta(seconds=int(rng.integers(10, 120)))
        new_events.append({
            "event_id": max_event_id,
            "user_id": user_id,
            "session_id": sid,
            "event_timestamp": payment_ts,
            "event_date": payment_ts.date(),
            "event_type": "payment_attempted",
            "device": device,
            "product_id": None,
            "page_url": None,
            "search_query": None,
            "app_version": checkout_evt.get("app_version"),
        })

        max_event_id += 1
        purchase_ts = payment_ts + timedelta(seconds=int(rng.integers(5, 60)))
        pid = int(rng.choice(products_df["product_id"].values))
        price = float(products_df[products_df["product_id"] == pid]["price"].iloc[0])

        new_events.append({
            "event_id": max_event_id,
            "user_id": user_id,
            "session_id": sid,
            "event_timestamp": purchase_ts,
            "event_date": purchase_ts.date(),
            "event_type": "purchase_complete",
            "device": device,
            "product_id": pid,
            "page_url": None,
            "search_query": None,
            "app_version": checkout_evt.get("app_version"),
        })

        # Create order
        max_order_id += 1
        max_item_id += 1
        discount_amt = round(price * 0.25, 2)  # Black Friday 25% off
        new_orders.append({
            "order_id": max_order_id,
            "user_id": user_id,
            "order_timestamp": purchase_ts,
            "order_date": purchase_ts.date(),
            "subtotal": price,
            "discount_amount": discount_amt,
            "shipping_amount": 5.99,
            "total_amount": round(price - discount_amt + 5.99, 2),
            "status": "completed",
            "promo_id": 3,  # Black Friday promo
            "is_plus_member_order": False,
            "device": device,
            "session_id": sid,
        })
        new_items.append({
            "order_item_id": max_item_id,
            "order_id": max_order_id,
            "product_id": pid,
            "quantity": 1,
            "unit_price": price,
            "discount_amount": discount_amt,
            "line_total": round(price - discount_amt, 2),
        })

    if new_events:
        events_df = pd.concat([events_df, pd.DataFrame(new_events)], ignore_index=True)
        orders_df = pd.concat([orders_df, pd.DataFrame(new_orders)], ignore_index=True)
        order_items_df = pd.concat([order_items_df, pd.DataFrame(new_items)], ignore_index=True)
        print(f"  Story 5 (Checkout Confound): injected {len(sessions_to_convert)} "
              f"promo-period purchases across {len(sessions_to_convert)} sessions")
    else:
        print(f"  Story 5 (Checkout Confound): no abandoned sessions to convert")

    return events_df, orders_df, order_items_df
