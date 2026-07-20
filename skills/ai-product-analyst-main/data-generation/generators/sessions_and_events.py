from __future__ import annotations

"""Generate sessions and events tables.

This is the most complex generator.  For each user, it creates sessions
across their active months (signup → end of year), then fills each session
with a realistic sequence of events following the e-commerce funnel.

The mobile checkout penalty is applied here: mobile devices convert at
60% of desktop rate at the checkout→payment and payment→purchase steps.

App versions are assigned based on device and date.

Processing is batched (5,000 users at a time) to keep memory manageable.
"""

import numpy as np
import pandas as pd
from tqdm import tqdm
from datetime import timedelta


def _get_app_version(device: str, event_date, app_versions_cfg: dict) -> str | None:
    """Return the app version string for a device on a given date."""
    if device == "web":
        return None
    versions = app_versions_cfg.get(device, [])
    date_str = str(event_date)
    for v in versions:
        if v["start"] <= date_str <= v["end"]:
            return v["version"]
    return versions[-1]["version"] if versions else None


def _generate_session_events(
    user_id: int,
    session_id: str,
    device: str,
    session_start: pd.Timestamp,
    n_events: int,
    funnel_cfg: dict,
    products_df: pd.DataFrame,
    app_version: str | None,
    rng: np.random.Generator,
) -> list[dict]:
    """Generate a list of event dicts for one session."""
    events = []
    is_mobile = device in ("ios", "android")
    mobile_penalty = funnel_cfg["mobile_checkout_penalty"]

    # First event: login or app_open
    ts = session_start
    if is_mobile and rng.random() < 0.3:
        events.append(_evt(user_id, session_id, ts, "app_open", device, app_version))
    else:
        events.append(_evt(user_id, session_id, ts, "login", device, app_version))

    # Remaining events: simulate browsing + funnel
    remaining = n_events - 1
    if remaining <= 0:
        return events

    # Sample some product ids for this session
    n_products_to_view = min(remaining, rng.integers(1, 6))
    viewed_products = rng.choice(products_df["product_id"].values, size=n_products_to_view, replace=True)

    events_generated = 0
    for pid in viewed_products:
        if events_generated >= remaining:
            break

        # Page view before product view
        ts = ts + timedelta(seconds=int(rng.integers(5, 120)))
        events.append(_evt(user_id, session_id, ts, "page_view", device, app_version,
                          page_url=f"/products/{pid}"))
        events_generated += 1
        if events_generated >= remaining:
            break

        # Product view
        ts = ts + timedelta(seconds=int(rng.integers(3, 60)))
        events.append(_evt(user_id, session_id, ts, "product_view", device, app_version,
                          product_id=int(pid)))
        events_generated += 1
        if events_generated >= remaining:
            break

        # Funnel: product_view → add_to_cart
        if rng.random() < funnel_cfg["product_view_to_add_to_cart"]:
            ts = ts + timedelta(seconds=int(rng.integers(5, 90)))
            events.append(_evt(user_id, session_id, ts, "add_to_cart", device, app_version,
                              product_id=int(pid)))
            events_generated += 1
            if events_generated >= remaining:
                break

            # Maybe save for later instead of proceeding
            if rng.random() < 0.15:
                ts = ts + timedelta(seconds=int(rng.integers(2, 30)))
                events.append(_evt(user_id, session_id, ts, "save_for_later", device, app_version,
                                  product_id=int(pid)))
                events_generated += 1
                if events_generated >= remaining:
                    break

            # add_to_cart → checkout_started
            if rng.random() < funnel_cfg["add_to_cart_to_checkout"]:
                ts = ts + timedelta(seconds=int(rng.integers(10, 180)))
                events.append(_evt(user_id, session_id, ts, "checkout_started", device, app_version))
                events_generated += 1
                if events_generated >= remaining:
                    break

                # checkout → payment (mobile penalty applies)
                pay_rate = funnel_cfg["checkout_to_payment"]
                if is_mobile:
                    pay_rate *= mobile_penalty
                if rng.random() < pay_rate:
                    ts = ts + timedelta(seconds=int(rng.integers(10, 120)))
                    events.append(_evt(user_id, session_id, ts, "payment_attempted", device, app_version))
                    events_generated += 1
                    if events_generated >= remaining:
                        break

                    # payment → purchase (no additional penalty — mobile already penalized at checkout)
                    purchase_rate = funnel_cfg["payment_to_purchase"]
                    if rng.random() < purchase_rate:
                        ts = ts + timedelta(seconds=int(rng.integers(5, 60)))
                        events.append(_evt(user_id, session_id, ts, "purchase_complete", device, app_version,
                                          product_id=int(pid)))
                        events_generated += 1
                        break  # Session ends after purchase

    # Fill remaining with page views / searches
    while events_generated < remaining:
        ts = ts + timedelta(seconds=int(rng.integers(5, 120)))
        if rng.random() < 0.3:
            events.append(_evt(user_id, session_id, ts, "search", device, app_version,
                              search_query=rng.choice(SEARCH_QUERIES)))
        else:
            events.append(_evt(user_id, session_id, ts, "page_view", device, app_version,
                              page_url=rng.choice(PAGE_URLS)))
        events_generated += 1

    return events


def _evt(user_id, session_id, ts, event_type, device, app_version,
         product_id=None, page_url=None, search_query=None):
    return {
        "user_id": user_id,
        "session_id": session_id,
        "event_timestamp": ts,
        "event_date": ts.date(),
        "event_type": event_type,
        "device": device,
        "product_id": product_id,
        "page_url": page_url,
        "search_query": search_query,
        "app_version": app_version,
    }


SEARCH_QUERIES = [
    "wireless headphones", "laptop bag", "running shoes", "yoga mat",
    "kitchen mixer", "moisturizer", "desk lamp", "fiction books",
    "phone case", "backpack", "winter jacket", "coffee maker",
    "bluetooth speaker", "face serum", "workout bands", "bed sheets",
    "tablet stand", "sunscreen", "hiking boots", "cookbook",
    "smart watch", "hair dryer", "protein powder", "storage bins",
    "noise canceling", "gift ideas", "sale items", "new arrivals",
]

PAGE_URLS = [
    "/", "/deals", "/categories", "/bestsellers", "/new-arrivals",
    "/account", "/orders", "/wishlist", "/cart", "/help",
    "/categories/electronics", "/categories/home", "/categories/clothing",
    "/categories/beauty", "/categories/sports", "/categories/books",
]


def _generate_activation_session(
    user_id: int,
    session_id: str,
    device: str,
    session_start: pd.Timestamp,
    products_df: pd.DataFrame,
    app_version: str | None,
    rng: np.random.Generator,
) -> list[dict]:
    """Generate a session that results in a purchase (for activated users)."""
    events = []
    ts = session_start

    # Login
    events.append(_evt(user_id, session_id, ts, "login", device, app_version))

    # Page view
    ts = ts + timedelta(seconds=int(rng.integers(10, 120)))
    pid = int(rng.choice(products_df["product_id"].values))
    events.append(_evt(user_id, session_id, ts, "page_view", device, app_version,
                      page_url=f"/products/{pid}"))

    # Product view
    ts = ts + timedelta(seconds=int(rng.integers(10, 60)))
    events.append(_evt(user_id, session_id, ts, "product_view", device, app_version,
                      product_id=pid))

    # Add to cart
    ts = ts + timedelta(seconds=int(rng.integers(10, 90)))
    events.append(_evt(user_id, session_id, ts, "add_to_cart", device, app_version,
                      product_id=pid))

    # Checkout
    ts = ts + timedelta(seconds=int(rng.integers(15, 180)))
    events.append(_evt(user_id, session_id, ts, "checkout_started", device, app_version))

    # Payment
    ts = ts + timedelta(seconds=int(rng.integers(10, 120)))
    events.append(_evt(user_id, session_id, ts, "payment_attempted", device, app_version))

    # Purchase
    ts = ts + timedelta(seconds=int(rng.integers(5, 60)))
    events.append(_evt(user_id, session_id, ts, "purchase_complete", device, app_version,
                      product_id=pid))

    return events


def generate(
    config: dict,
    users_df: pd.DataFrame,
    products_df: pd.DataFrame,
    calendar_df: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate events and sessions DataFrames."""
    sess_cfg = config["sessions"]
    funnel_cfg = config["funnel"]
    app_ver_cfg = config["app_versions"]
    activation_cfg = config["activation"]
    end_date = pd.Timestamp(config["general"]["time_range"][1])

    avg_sessions_per_month = sess_cfg["avg_sessions_per_user_per_month"]
    evt_mean = sess_cfg["events_per_session"]["mean"]
    evt_std = sess_cfg["events_per_session"]["std"]
    evt_min = sess_cfg["events_per_session"]["min"]
    evt_max = sess_cfg["events_per_session"]["max"]

    all_events = []
    all_sessions = []
    session_counter = 0

    batch_size = 5000
    n_users = len(users_df)

    for batch_start in tqdm(range(0, n_users, batch_size), desc="Generating events"):
        batch_end = min(batch_start + batch_size, n_users)
        batch_users = users_df.iloc[batch_start:batch_end]

        for _, user in batch_users.iterrows():
            user_id = user["user_id"]
            signup_ts = pd.Timestamp(user["signup_timestamp"])
            device_primary = user["device_primary"]
            channel = user["acquisition_channel"]

            # --- Activation: should this user purchase within 7 days? ---
            activation_rate = activation_cfg.get(channel, 0.25)
            should_activate = rng.random() < activation_rate

            if should_activate:
                # Generate an activation session (guaranteed purchase) within 7 days
                session_counter += 1
                sid = f"s_{user_id}_{session_counter}"
                activation_day = int(rng.integers(1, 8))  # 1-7 days after signup
                activation_ts = signup_ts + timedelta(days=activation_day,
                                                     hours=int(rng.integers(9, 21)))
                if activation_ts > end_date:
                    activation_ts = end_date - timedelta(hours=1)

                device = device_primary
                app_version = _get_app_version(device, activation_ts.date(), app_ver_cfg)

                session_events = _generate_activation_session(
                    user_id, sid, device, activation_ts,
                    products_df, app_version, rng
                )
                all_events.extend(session_events)

                timestamps = [e["event_timestamp"] for e in session_events]
                all_sessions.append({
                    "session_id": sid,
                    "user_id": user_id,
                    "session_start": min(timestamps),
                    "session_end": max(timestamps),
                    "session_date": activation_ts.date(),
                    "device": device,
                    "landing_page": f"/products/{session_events[2]['product_id']}",
                    "page_views": 1,
                    "events_count": len(session_events),
                    "had_purchase": True,
                })

            # --- Regular sessions ---
            # How many months is user active?
            months_active = max(1, (end_date.month - signup_ts.month) +
                              12 * (end_date.year - signup_ts.year) + 1)

            # Total sessions for this user (Poisson around avg * months)
            expected_sessions = avg_sessions_per_month * months_active
            n_sessions = max(1, int(rng.poisson(expected_sessions)))

            # Distribute session dates across active period
            total_seconds = int((end_date - signup_ts).total_seconds())
            if total_seconds <= 0:
                total_seconds = 86400  # at least one day

            for _ in range(n_sessions):
                session_counter += 1
                sid = f"s_{user_id}_{session_counter}"

                # Random session start time after signup
                offset_seconds = rng.integers(0, max(1, total_seconds))
                session_start = signup_ts + timedelta(seconds=int(offset_seconds))

                # Device: 70% primary, 30% random
                if rng.random() < 0.70:
                    device = device_primary
                else:
                    device = rng.choice(["web", "ios", "android"])

                # App version for this device/date
                app_version = _get_app_version(device, session_start.date(), app_ver_cfg)

                # Number of events in session
                n_events = int(rng.normal(evt_mean, evt_std))
                n_events = max(evt_min, min(evt_max, n_events))

                # Generate events
                session_events = _generate_session_events(
                    user_id, sid, device, session_start, n_events,
                    funnel_cfg, products_df, app_version, rng
                )

                all_events.extend(session_events)

                # Build session summary
                if session_events:
                    timestamps = [e["event_timestamp"] for e in session_events]
                    page_views = sum(1 for e in session_events if e["event_type"] == "page_view")
                    had_purchase = any(e["event_type"] == "purchase_complete" for e in session_events)
                    landing = next((e["page_url"] for e in session_events if e["page_url"]), "/")

                    all_sessions.append({
                        "session_id": sid,
                        "user_id": user_id,
                        "session_start": min(timestamps),
                        "session_end": max(timestamps),
                        "session_date": session_start.date(),
                        "device": device,
                        "landing_page": landing,
                        "page_views": page_views,
                        "events_count": len(session_events),
                        "had_purchase": had_purchase,
                    })

    # Build DataFrames
    events_df = pd.DataFrame(all_events)
    events_df.insert(0, "event_id", range(1, len(events_df) + 1))

    sessions_df = pd.DataFrame(all_sessions)

    print(f"  Generated {len(events_df):,} events across {len(sessions_df):,} sessions")
    return sessions_df, events_df
