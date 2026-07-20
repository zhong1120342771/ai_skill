from __future__ import annotations

"""Story 4: Power User Fallacy — Save for Later correlation vs causation.

This script ensures:
1. Observational: users with save_for_later events have ~3x purchase rate
   (already embedded because high-intent users naturally do both)
2. Experimental: the save_for_later_visibility experiment shows only ~8%
   relative lift (treatment 16.5% vs control 15.3%)

The observational correlation should already exist from the events generator
because high-engagement users both use save_for_later AND purchase more.

For the experiment, we need to ensure the experiment_assignments + orders
data produces the right treatment effect.  We do this by injecting a small
number of additional purchases for treatment users.
"""

import numpy as np
import pandas as pd
from datetime import timedelta


def inject(
    events_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    order_items_df: pd.DataFrame,
    experiment_assignments_df: pd.DataFrame,
    products_df: pd.DataFrame,
    config: dict,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Adjust experiment outcomes to produce the target treatment effect.

    Returns modified (events_df, orders_df, order_items_df).
    """
    cfg = config["stories"]["power_user_fallacy"]
    exp_id = cfg["experiment_id"]
    target_control_rate = cfg["control_purchase_rate"]
    target_treatment_rate = cfg["treatment_purchase_rate"]

    # Get experiment 1 assignments
    exp_assigns = experiment_assignments_df[
        experiment_assignments_df["experiment_id"] == exp_id
    ].copy()

    if len(exp_assigns) == 0:
        print("  Story 4 (Power User Fallacy): No experiment assignments found, skipping")
        return events_df, orders_df, order_items_df

    exp_start = pd.Timestamp(cfg["experiment_start"])
    exp_end = pd.Timestamp(cfg["experiment_end"])

    # Calculate current purchase rates within 30 days of assignment
    control_users = set(exp_assigns[exp_assigns["variant"] == "control"]["user_id"])
    treatment_users = set(exp_assigns[exp_assigns["variant"] == "treatment"]["user_id"])

    # Get orders within experiment window
    orders_in_window = orders_df[
        (pd.to_datetime(orders_df["order_date"]) >= exp_start) &
        (pd.to_datetime(orders_df["order_date"]) <= exp_end) &
        (orders_df["status"] == "completed")
    ]

    control_purchasers = set(orders_in_window[orders_in_window["user_id"].isin(control_users)]["user_id"])
    treatment_purchasers = set(orders_in_window[orders_in_window["user_id"].isin(treatment_users)]["user_id"])

    current_control_rate = len(control_purchasers) / max(1, len(control_users))
    current_treatment_rate = len(treatment_purchasers) / max(1, len(treatment_users))

    print(f"  Story 4 (Power User Fallacy): current rates — "
          f"control={current_control_rate:.3f}, treatment={current_treatment_rate:.3f}")

    # We need treatment rate to be ~target_treatment_rate
    # Add extra purchases for treatment users who haven't purchased
    treatment_non_purchasers = list(treatment_users - treatment_purchasers)
    needed_extra = int(target_treatment_rate * len(treatment_users)) - len(treatment_purchasers)

    if needed_extra > 0 and len(treatment_non_purchasers) > 0:
        n_to_add = min(needed_extra, len(treatment_non_purchasers))
        users_to_convert = rng.choice(treatment_non_purchasers, size=n_to_add, replace=False)

        max_event_id = events_df["event_id"].max()
        max_order_id = orders_df["order_id"].max()
        max_item_id = order_items_df["order_item_id"].max()

        new_events = []
        new_orders = []
        new_items = []

        for uid in users_to_convert:
            # Create a purchase event + order during experiment window
            days_offset = int(rng.integers(7, 50))
            purchase_ts = exp_start + timedelta(days=days_offset)
            if purchase_ts > exp_end:
                purchase_ts = exp_end - timedelta(days=int(rng.integers(1, 10)))

            max_event_id += 1
            sid = f"s_{uid}_exp1_{max_event_id}"
            pid = int(rng.choice(products_df["product_id"].values))
            price = float(products_df[products_df["product_id"] == pid]["price"].iloc[0])

            new_events.append({
                "event_id": max_event_id,
                "user_id": uid,
                "session_id": sid,
                "event_timestamp": purchase_ts,
                "event_date": purchase_ts.date(),
                "event_type": "purchase_complete",
                "device": rng.choice(["web", "ios", "android"]),
                "product_id": pid,
                "page_url": None,
                "search_query": None,
                "app_version": None,
            })

            max_order_id += 1
            max_item_id += 1
            new_orders.append({
                "order_id": max_order_id,
                "user_id": uid,
                "order_timestamp": purchase_ts,
                "order_date": purchase_ts.date(),
                "subtotal": price,
                "discount_amount": 0.0,
                "shipping_amount": 5.99,
                "total_amount": round(price + 5.99, 2),
                "status": "completed",
                "promo_id": None,
                "is_plus_member_order": False,
                "device": "web",
                "session_id": sid,
            })
            new_items.append({
                "order_item_id": max_item_id,
                "order_id": max_order_id,
                "product_id": pid,
                "quantity": 1,
                "unit_price": price,
                "discount_amount": 0.0,
                "line_total": price,
            })

        if new_events:
            events_df = pd.concat([events_df, pd.DataFrame(new_events)], ignore_index=True)
            orders_df = pd.concat([orders_df, pd.DataFrame(new_orders)], ignore_index=True)
            order_items_df = pd.concat([order_items_df, pd.DataFrame(new_items)], ignore_index=True)
            print(f"  Story 4: injected {len(new_events)} extra treatment purchases")
    else:
        print(f"  Story 4: no injection needed (rates already in range)")

    return events_df, orders_df, order_items_df
