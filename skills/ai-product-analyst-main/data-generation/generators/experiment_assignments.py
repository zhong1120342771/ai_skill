"""Generate experiment_assignments table (~20K rows).

Two experiments:
  1. save_for_later_visibility: 10K users, Aug-Sep 2024, 50/50 split
  2. checkout_redesign: 10K mobile users, Nov 20 - Dec 31, 50/50 split

Random assignment, balanced on key dimensions.
"""

import numpy as np
import pandas as pd


def generate(
    config: dict,
    users_df: pd.DataFrame,
    experiments_df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    stories_cfg = config["stories"]
    rows = []
    assignment_id = 0

    # --- Experiment 1: Save for Later Visibility ---
    exp1_cfg = stories_cfg["power_user_fallacy"]
    exp1_start = pd.Timestamp(exp1_cfg["experiment_start"])
    exp1_end = pd.Timestamp(exp1_cfg["experiment_end"])
    n_exp1 = exp1_cfg["n_experiment_users"]

    # Eligible: users who signed up before experiment start
    eligible_1 = users_df[pd.to_datetime(users_df["signup_date"]) < exp1_start]
    if len(eligible_1) >= n_exp1:
        selected_1 = eligible_1.sample(n=n_exp1, random_state=int(rng.integers(0, 2**31)))
    else:
        selected_1 = eligible_1

    for i, (_, user) in enumerate(selected_1.iterrows()):
        assignment_id += 1
        variant = "control" if i % 2 == 0 else "treatment"  # Perfect 50/50
        assigned_date = exp1_start + pd.Timedelta(days=int(rng.integers(0, 7)))
        exposure_offset = int(rng.integers(0, 14))
        first_exposure = assigned_date + pd.Timedelta(days=exposure_offset)
        if first_exposure > exp1_end:
            first_exposure = None
        else:
            first_exposure = first_exposure.date()

        rows.append({
            "assignment_id": assignment_id,
            "experiment_id": exp1_cfg["experiment_id"],
            "user_id": user["user_id"],
            "variant": variant,
            "assigned_date": assigned_date.date(),
            "first_exposure_date": first_exposure,
        })

    # --- Experiment 2: Checkout Redesign ---
    exp2_cfg = stories_cfg["checkout_confound"]
    exp2_start = pd.Timestamp(exp2_cfg["redesign_date"])
    n_exp2 = exp2_cfg["n_experiment_users"]

    # Eligible: mobile users who signed up before experiment start
    eligible_2 = users_df[
        (pd.to_datetime(users_df["signup_date"]) < exp2_start) &
        (users_df["device_primary"].isin(["ios", "android"]))
    ]
    if len(eligible_2) >= n_exp2:
        selected_2 = eligible_2.sample(n=n_exp2, random_state=int(rng.integers(0, 2**31)))
    else:
        selected_2 = eligible_2

    exp2_end = pd.Timestamp(config["general"]["time_range"][1])
    for i, (_, user) in enumerate(selected_2.iterrows()):
        assignment_id += 1
        variant = "control" if i % 2 == 0 else "treatment"
        assigned_date = exp2_start
        exposure_offset = int(rng.integers(0, 7))
        first_exposure = assigned_date + pd.Timedelta(days=exposure_offset)
        if first_exposure > exp2_end:
            first_exposure = None
        else:
            first_exposure = first_exposure.date()

        rows.append({
            "assignment_id": assignment_id,
            "experiment_id": exp2_cfg["experiment_id"],
            "user_id": user["user_id"],
            "variant": variant,
            "assigned_date": assigned_date.date(),
            "first_exposure_date": first_exposure,
        })

    df = pd.DataFrame(rows)
    print(f"  Generated {len(df):,} experiment assignments")
    return df
