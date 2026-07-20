"""Generate the support_tickets table (~25K rows).

Base rate: 2.5 tickets per 1,000 active users per day.
The ticket spike (Story 1) is injected separately by stories/ticket_spike.py.
"""

import numpy as np
import pandas as pd
from datetime import timedelta


def generate(
    config: dict,
    users_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    app_versions_cfg: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    cfg = config["support_tickets"]
    base_rate = cfg["base_rate_per_1000_users_per_day"]
    cat_dist = cfg["category_distribution"]
    sev_dist = cfg["severity_distribution"]
    res_cfg = cfg["resolution_hours"]

    categories = list(cat_dist.keys())
    cat_probs = list(cat_dist.values())
    severities = list(sev_dist.keys())
    sev_probs = list(sev_dist.values())

    start_date = pd.Timestamp(config["general"]["time_range"][0])
    end_date = pd.Timestamp(config["general"]["time_range"][1])

    # Build cumulative user count by date (users who signed up by that date)
    signup_dates = pd.to_datetime(users_df["signup_date"])
    user_ids = users_df["user_id"].values
    user_devices = dict(zip(users_df["user_id"], users_df["device_primary"]))

    # Order ids by user for linking
    order_user_map = {}
    if orders_df is not None and len(orders_df) > 0:
        for uid, group in orders_df.groupby("user_id"):
            order_user_map[uid] = group["order_id"].tolist()

    rows = []
    ticket_id = 0

    dates = pd.date_range(start_date, end_date, freq="D")

    for day in dates:
        # Count users who signed up by this date
        active_users = int((signup_dates <= day).sum())
        if active_users == 0:
            continue

        # Expected tickets today
        expected = base_rate * active_users / 1000.0
        n_tickets = rng.poisson(expected)

        # Get eligible users (signed up by this date)
        eligible_mask = signup_dates <= day
        eligible_ids = user_ids[eligible_mask]

        for _ in range(n_tickets):
            ticket_id += 1
            uid = int(rng.choice(eligible_ids))
            device = user_devices.get(uid, "web")

            # Random time of day
            hour = int(rng.normal(14, 4))  # Peak around 2pm
            hour = max(0, min(23, hour))
            minute = int(rng.integers(0, 60))
            created_at = day + timedelta(hours=hour, minutes=minute)

            category = rng.choice(categories, p=cat_probs)
            severity = rng.choice(severities, p=sev_probs)

            # Resolution time
            res_hours = rng.normal(res_cfg["mean"], res_cfg["std"])
            res_hours = max(res_cfg["min"], min(res_cfg["max"], res_hours))
            resolved_at = created_at + timedelta(hours=res_hours)

            # Status
            if rng.random() < 0.05:
                status = "open"
                resolved_at = None
            elif rng.random() < 0.80:
                status = "resolved"
            else:
                status = "closed"

            # App version
            app_version = None
            if device in ("ios", "android"):
                for v in app_versions_cfg.get(device, []):
                    if v["start"] <= str(day.date()) <= v["end"]:
                        app_version = v["version"]
                        break

            # Link to order (~60% of tickets)
            order_id = None
            if rng.random() < 0.60 and uid in order_user_map:
                user_orders = order_user_map[uid]
                if user_orders:
                    order_id = int(rng.choice(user_orders))

            rows.append({
                "ticket_id": ticket_id,
                "user_id": uid,
                "created_at": created_at,
                "created_date": day.date(),
                "category": category,
                "severity": severity,
                "status": status,
                "resolved_at": resolved_at,
                "device": device,
                "app_version": app_version,
                "order_id": order_id,
            })

    df = pd.DataFrame(rows)
    print(f"  Generated {len(df):,} support tickets")
    return df
