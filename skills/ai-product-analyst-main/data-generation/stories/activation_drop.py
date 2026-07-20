"""Story 2: Activation Drop / Channel Mix Shift.

This story is primarily implemented in users.py (TikTok channel appears
Jun 1+) and sessions_and_events.py (TikTok users have lower purchase
intent via fewer sessions and lower funnel conversion).

This script validates the pattern exists and reports on it.  It does NOT
modify data — the story should already be embedded by the generators.
"""

import pandas as pd
import numpy as np


def validate(
    users_df: pd.DataFrame,
    orders_df: pd.DataFrame,
    config: dict,
) -> dict:
    """Validate that Story 2 pattern is present. Returns diagnostics."""
    tiktok_launch = pd.Timestamp(config["users"]["tiktok_launch_date"])

    users = users_df.copy()
    users["signup_date_ts"] = pd.to_datetime(users["signup_date"])

    # Join to find first order within 7 days
    if orders_df is not None and len(orders_df) > 0:
        first_orders = orders_df.groupby("user_id")["order_date"].min().reset_index()
        first_orders.columns = ["user_id", "first_order_date"]
        first_orders["first_order_date"] = pd.to_datetime(first_orders["first_order_date"])
        users = users.merge(first_orders, on="user_id", how="left")
    else:
        users["first_order_date"] = pd.NaT

    # 7-day activation
    users["activated"] = (
        users["first_order_date"].notna() &
        ((users["first_order_date"] - users["signup_date_ts"]).dt.days <= 7)
    )

    users["period"] = np.where(users["signup_date_ts"] < tiktok_launch, "pre", "post")

    # Overall rates
    overall = users.groupby("period")["activated"].mean()
    pre_rate = overall.get("pre", 0)
    post_rate = overall.get("post", 0)

    # By channel
    by_channel = users.groupby(["period", "acquisition_channel"])["activated"].agg(["mean", "count"])

    diagnostics = {
        "pre_activation_rate": round(pre_rate, 4),
        "post_activation_rate": round(post_rate, 4),
        "drop_pp": round(pre_rate - post_rate, 4),
        "by_channel": by_channel.to_dict(),
        "tiktok_post_share": 0,
    }

    # TikTok share of post-launch signups
    post_users = users[users["period"] == "post"]
    if len(post_users) > 0:
        tiktok_share = (post_users["acquisition_channel"] == "tiktok_ads").mean()
        diagnostics["tiktok_post_share"] = round(tiktok_share, 4)
        tiktok_activation = post_users[post_users["acquisition_channel"] == "tiktok_ads"]["activated"].mean()
        diagnostics["tiktok_activation_rate"] = round(tiktok_activation, 4) if not pd.isna(tiktok_activation) else 0

    print(f"  Story 2 (Activation Drop): pre={pre_rate:.1%}, post={post_rate:.1%}, "
          f"drop={pre_rate - post_rate:.1%}, TikTok share={diagnostics['tiktok_post_share']:.1%}")

    return diagnostics
