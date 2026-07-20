from __future__ import annotations

"""Apply data quality landmines to create the capstone dataset.

Takes copies of the practice DataFrames and introduces:
1. Duplicate Android events (2%)
2. Missing iOS events for Oct 1-7
3. Delayed timestamps on 3% of events (+7 hours)
4. Orphan orders (1% reference nonexistent user_ids)
5. NULL device on 30% of support tickets
6. Remove sessions table
7. Remove user_segment from nps_responses
"""

import numpy as np
import pandas as pd
from datetime import timedelta


def apply_landmines(
    tables: dict[str, pd.DataFrame],
    config: dict,
    rng: np.random.Generator,
) -> dict[str, pd.DataFrame]:
    """Apply all capstone modifications.  Returns modified dict of DataFrames."""
    cfg = config["capstone"]["landmines"]
    structural = config["capstone"]["structural"]

    result = {}
    for name, df in tables.items():
        result[name] = df.copy()

    # --- 1. Duplicate Android events (2%) ---
    events = result["events"]
    android_mask = events["device"] == "android"
    android_events = events[android_mask]
    n_dupes = int(len(android_events) * cfg["duplicate_android_events_pct"])
    if n_dupes > 0:
        dupe_idx = rng.choice(android_events.index, size=n_dupes, replace=False)
        dupes = events.loc[dupe_idx].copy()
        events = pd.concat([events, dupes], ignore_index=True)
        events = events.sort_values("event_timestamp").reset_index(drop=True)
        # Note: duplicate event_ids are intentional — that's the landmine
        print(f"  Landmine 1: duplicated {n_dupes:,} Android events")
    result["events"] = events

    # --- 2. Missing iOS events for specified window ---
    missing_start = pd.Timestamp(cfg["missing_ios_events_window"][0])
    missing_end = pd.Timestamp(cfg["missing_ios_events_window"][1])
    events = result["events"]
    ios_gap_mask = (
        (events["device"] == "ios") &
        (pd.to_datetime(events["event_date"]) >= missing_start) &
        (pd.to_datetime(events["event_date"]) <= missing_end)
    )
    n_removed = ios_gap_mask.sum()
    events = events[~ios_gap_mask].reset_index(drop=True)
    print(f"  Landmine 2: removed {n_removed:,} iOS events for {cfg['missing_ios_events_window']}")
    result["events"] = events

    # --- 3. Delayed timestamps on 3% of events (+7 hours) ---
    events = result["events"]
    n_delayed = int(len(events) * cfg["delayed_timestamp_pct"])
    delay_idx = rng.choice(len(events), size=n_delayed, replace=False)
    shift = timedelta(hours=cfg["delayed_timestamp_shift_hours"])
    events.loc[events.index[delay_idx], "event_timestamp"] = (
        pd.to_datetime(events.loc[events.index[delay_idx], "event_timestamp"]) + shift
    )
    print(f"  Landmine 3: shifted {n_delayed:,} event timestamps by +{cfg['delayed_timestamp_shift_hours']}h")
    result["events"] = events

    # --- 4. Orphan orders (1% reference nonexistent user_ids) ---
    orders = result["orders"]
    n_orphans = int(len(orders) * cfg["orphan_order_pct"])
    if n_orphans > 0:
        orphan_idx = rng.choice(len(orders), size=n_orphans, replace=False)
        max_user_id = result["users"]["user_id"].max()
        # Assign user_ids that don't exist in users table
        fake_ids = np.arange(max_user_id + 1000, max_user_id + 1000 + n_orphans)
        orders.loc[orders.index[orphan_idx], "user_id"] = fake_ids
        print(f"  Landmine 4: created {n_orphans:,} orphan orders")
    result["orders"] = orders

    # --- 5. NULL device on 30% of support tickets ---
    tickets = result["support_tickets"]
    n_null_device = int(len(tickets) * structural["null_support_device_pct"])
    null_idx = rng.choice(len(tickets), size=n_null_device, replace=False)
    tickets.loc[tickets.index[null_idx], "device"] = None
    print(f"  Landmine 5: set {n_null_device:,} support ticket devices to NULL")
    result["support_tickets"] = tickets

    # --- 6. Remove sessions table ---
    if structural.get("remove_sessions_table", False):
        if "sessions" in result:
            del result["sessions"]
            print(f"  Landmine 6: removed sessions table")

    # --- 7. Remove user_segment from nps_responses ---
    if structural.get("remove_nps_user_segment", False):
        if "user_segment" in result["nps_responses"].columns:
            result["nps_responses"] = result["nps_responses"].drop(columns=["user_segment"])
            print(f"  Landmine 7: removed user_segment from nps_responses")

    # --- 5b. Unstitched sessions (5%) ---
    # Break session_id linkage for 5% of sessions (vectorized)
    events = result["events"]
    unique_sessions = events["session_id"].unique()
    n_unstitch = int(len(unique_sessions) * cfg["unstitched_sessions_pct"])
    if n_unstitch > 0:
        sessions_to_break = set(rng.choice(unique_sessions, size=n_unstitch, replace=False))
        # For each event in a broken session, assign the second half a new session_id
        # We use cumcount within each session to determine the midpoint
        mask = events["session_id"].isin(sessions_to_break)
        broken_events = events[mask].copy()
        # Assign a rank within each session
        broken_events["_rank"] = broken_events.groupby("session_id").cumcount()
        broken_events["_size"] = broken_events.groupby("session_id")["_rank"].transform("max") + 1
        # Second half gets "_broken" suffix
        is_second_half = (broken_events["_rank"] >= broken_events["_size"] // 2) & (broken_events["_size"] > 1)
        broken_events.loc[is_second_half, "session_id"] = broken_events.loc[is_second_half, "session_id"] + "_broken"
        # Write back
        events.loc[mask, "session_id"] = broken_events["session_id"].values
        print(f"  Landmine 5b: broke {n_unstitch:,} session linkages")
    result["events"] = events

    return result
