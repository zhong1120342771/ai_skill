"""Generate the memberships table (~12K rows).

State machine per user:
  - 8% of users start a trial within 30 days of signup
  - 45% of trials convert to paid (60% monthly, 40% annual)
  - Monthly churn: 5%/month, annual churn: 2%/month
  - Tracks state transitions as separate rows
"""

import numpy as np
import pandas as pd
from datetime import timedelta


CANCEL_REASONS = ["price", "not_using", "competitor", "other"]
CANCEL_REASON_PROBS = [0.35, 0.30, 0.15, 0.20]


def generate(
    config: dict,
    users_df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    cfg = config["membership"]
    end_date = pd.Timestamp(config["general"]["time_range"][1])

    trial_rate = cfg["trial_rate"]
    trial_to_paid = cfg["trial_to_paid_rate"]
    monthly_churn = cfg["monthly_churn_rate"]
    annual_churn = cfg["annual_churn_rate"]
    plan_split = cfg["plan_split"]

    rows = []
    membership_id = 0

    for _, user in users_df.iterrows():
        user_id = user["user_id"]
        signup_ts = pd.Timestamp(user["signup_timestamp"])

        # Does this user start a trial?
        if rng.random() >= trial_rate:
            continue

        # Trial starts 1-30 days after signup
        trial_offset = int(rng.integers(1, 31))
        trial_start = signup_ts + timedelta(days=trial_offset)
        if trial_start > end_date:
            continue

        trial_end = trial_start + timedelta(days=14)  # 14-day trial

        membership_id += 1

        # Does trial convert?
        if rng.random() < trial_to_paid:
            # Trial → converted
            rows.append({
                "membership_id": membership_id,
                "user_id": user_id,
                "plan_type": "plus_trial",
                "started_at": trial_start,
                "ended_at": trial_end,
                "status": "converted",
                "cancel_reason": None,
                "is_current": False,
            })

            # Start paid membership
            plan = "plus_monthly" if rng.random() < plan_split["monthly"] else "plus_annual"
            churn_rate = monthly_churn if plan == "plus_monthly" else annual_churn
            paid_start = trial_end

            # Simulate months of membership
            current_start = paid_start
            still_active = True

            while still_active and current_start < end_date:
                # Check for churn this month
                if rng.random() < churn_rate:
                    # Churned
                    churn_day = int(rng.integers(1, 29))
                    churn_date = current_start + timedelta(days=churn_day)
                    if churn_date > end_date:
                        churn_date = end_date

                    membership_id += 1
                    reason = rng.choice(CANCEL_REASONS, p=CANCEL_REASON_PROBS)
                    rows.append({
                        "membership_id": membership_id,
                        "user_id": user_id,
                        "plan_type": plan,
                        "started_at": current_start,
                        "ended_at": churn_date,
                        "status": "cancelled",
                        "cancel_reason": reason,
                        "is_current": False,
                    })
                    still_active = False
                else:
                    # Survived this month, advance
                    next_month = current_start + timedelta(days=30)
                    if next_month >= end_date:
                        # Still active at end of data
                        membership_id += 1
                        rows.append({
                            "membership_id": membership_id,
                            "user_id": user_id,
                            "plan_type": plan,
                            "started_at": current_start,
                            "ended_at": None,
                            "status": "active",
                            "cancel_reason": None,
                            "is_current": True,
                        })
                        still_active = False
                    else:
                        current_start = next_month
            else:
                # If we exited the while without breaking, user is still active
                if still_active:
                    membership_id += 1
                    rows.append({
                        "membership_id": membership_id,
                        "user_id": user_id,
                        "plan_type": plan,
                        "started_at": current_start,
                        "ended_at": None,
                        "status": "active",
                        "cancel_reason": None,
                        "is_current": True,
                    })
        else:
            # Trial expired
            if trial_end > end_date:
                trial_end = end_date
            rows.append({
                "membership_id": membership_id,
                "user_id": user_id,
                "plan_type": "plus_trial",
                "started_at": trial_start,
                "ended_at": trial_end,
                "status": "expired",
                "cancel_reason": None,
                "is_current": False,
            })

    df = pd.DataFrame(rows)
    print(f"  Generated {len(df):,} membership records")
    return df
