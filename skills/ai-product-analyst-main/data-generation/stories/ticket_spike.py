"""Story 1: Support Ticket Spike — iOS v2.3 payment bug.

Injects extra payment_issue tickets for iOS v2.3 during Jun 1-14, 2024.
The spike is 3x the baseline for payment_issue tickets, concentrated
entirely on iOS with app_version='2.3.0'.
"""

import numpy as np
import pandas as pd
from datetime import timedelta


def inject(
    support_tickets_df: pd.DataFrame,
    users_df: pd.DataFrame,
    config: dict,
    rng: np.random.Generator,
) -> pd.DataFrame:
    cfg = config["stories"]["ticket_spike"]
    spike_start = pd.Timestamp(cfg["start"])
    spike_end = pd.Timestamp(cfg["end"])
    multiplier = cfg["multiplier"]
    category = cfg["category"]
    device = cfg["device"]
    app_version = cfg["app_version"]

    # Calculate baseline: avg daily payment_issue tickets outside spike period
    df = support_tickets_df.copy()
    non_spike = df[
        (df["category"] == category) &
        ((pd.to_datetime(df["created_date"]) < spike_start) |
         (pd.to_datetime(df["created_date"]) > spike_end))
    ]
    n_non_spike_days = len(pd.date_range(
        config["general"]["time_range"][0],
        config["general"]["time_range"][1],
        freq="D"
    )) - (spike_end - spike_start).days - 1
    baseline_daily = len(non_spike) / max(1, n_non_spike_days)

    # How many extra tickets to add per day during spike
    extra_per_day = int(baseline_daily * (multiplier - 1))
    spike_days = pd.date_range(spike_start, spike_end, freq="D")

    # Get iOS users
    ios_users = users_df[users_df["device_primary"] == "ios"]["user_id"].values
    if len(ios_users) == 0:
        ios_users = users_df["user_id"].values

    max_ticket_id = df["ticket_id"].max()
    new_rows = []

    for day in spike_days:
        for i in range(extra_per_day):
            max_ticket_id += 1
            uid = int(rng.choice(ios_users))
            hour = int(rng.normal(14, 4))
            hour = max(0, min(23, hour))
            minute = int(rng.integers(0, 60))
            created_at = day + timedelta(hours=hour, minutes=minute)

            severity = rng.choice(
                ["low", "medium", "high", "critical"],
                p=[0.20, 0.30, 0.35, 0.15]  # Higher severity during spike
            )

            res_hours = rng.normal(30, 15)  # Slower resolution during spike
            res_hours = max(1, min(72, res_hours))
            resolved_at = created_at + timedelta(hours=res_hours)

            if rng.random() < 0.15:  # More open tickets during spike
                status = "open"
                resolved_at = None
            else:
                status = "resolved"

            new_rows.append({
                "ticket_id": max_ticket_id,
                "user_id": uid,
                "created_at": created_at,
                "created_date": day.date(),
                "category": category,
                "severity": severity,
                "status": status,
                "resolved_at": resolved_at,
                "device": device,
                "app_version": app_version,
                "order_id": None,
            })

    if new_rows:
        new_df = pd.DataFrame(new_rows)
        df = pd.concat([df, new_df], ignore_index=True)
        df = df.sort_values("created_at").reset_index(drop=True)
        # Re-assign ticket_ids sequentially
        df["ticket_id"] = range(1, len(df) + 1)

    print(f"  Story 1 (Ticket Spike): injected {len(new_rows)} extra tickets for Jun 1-14")
    return df
