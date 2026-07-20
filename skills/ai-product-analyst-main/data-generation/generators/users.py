"""Generate the users dimension table (~50,000 rows).

Handles the TikTok channel launch on Jun 1 — before that date, tiktok_ads
share is 0% and redistributed to other channels.  After Jun 1, tiktok_ads
ramps up to its configured post-launch share.
"""

import numpy as np
import pandas as pd


def generate(config: dict, calendar_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    cfg = config["users"]
    n = cfg["n_users"]
    start_date = pd.Timestamp(config["general"]["time_range"][0])
    end_date = pd.Timestamp(config["general"]["time_range"][1])
    tiktok_launch = pd.Timestamp(cfg["tiktok_launch_date"])

    # --- Signup dates: linear growth curve ---
    total_days = (end_date - start_date).days + 1
    # Linear weights: day 1 gets weight 1, last day gets weight ~1.5
    day_weights = np.linspace(1.0, 1.5, total_days)
    day_probs = day_weights / day_weights.sum()
    day_offsets = rng.choice(total_days, size=n, p=day_probs)
    signup_dates = pd.to_datetime(start_date) + pd.to_timedelta(day_offsets, unit="D")
    signup_dates = pd.Series(signup_dates).sort_values().reset_index(drop=True)

    # Random time-of-day for signup_timestamp
    seconds_in_day = 86400
    random_seconds = rng.integers(0, seconds_in_day, size=n)
    signup_timestamps = signup_dates + pd.to_timedelta(random_seconds, unit="s")

    # --- Acquisition channel ---
    channels = list(cfg["acquisition_channels"].keys())
    base_probs = np.array(list(cfg["acquisition_channels"].values()))

    # Pre-TikTok probabilities (redistribute tiktok share)
    tiktok_idx = channels.index("tiktok_ads")
    pre_probs = base_probs.copy()
    pre_probs[tiktok_idx] = 0.0
    pre_probs = pre_probs / pre_probs.sum()

    # Post-TikTok probabilities (tiktok gets its post-launch share)
    post_tiktok_share = cfg["tiktok_post_launch_share"]
    post_probs = base_probs.copy()
    post_probs[tiktok_idx] = post_tiktok_share
    # Scale others so they sum to (1 - post_tiktok_share)
    others_sum = post_probs[:tiktok_idx].sum() + post_probs[tiktok_idx + 1:].sum()
    scale = (1.0 - post_tiktok_share) / others_sum
    for i in range(len(post_probs)):
        if i != tiktok_idx:
            post_probs[i] *= scale

    is_post_tiktok = signup_dates >= tiktok_launch
    acquisition = np.empty(n, dtype=object)
    pre_mask = ~is_post_tiktok
    if pre_mask.sum() > 0:
        acquisition[pre_mask] = rng.choice(channels, size=pre_mask.sum(), p=pre_probs)
    if is_post_tiktok.sum() > 0:
        acquisition[is_post_tiktok] = rng.choice(channels, size=is_post_tiktok.sum(), p=post_probs)

    # --- Country ---
    countries = list(cfg["countries"].keys())
    country_probs = list(cfg["countries"].values())
    user_countries = rng.choice(countries, size=n, p=country_probs)

    # --- Device ---
    devices = list(cfg["devices"].keys())
    device_probs = list(cfg["devices"].values())
    user_devices = rng.choice(devices, size=n, p=device_probs)

    # --- Age bucket ---
    age_buckets = list(cfg["age_buckets"].keys())
    age_probs = list(cfg["age_buckets"].values())
    user_ages = rng.choice(age_buckets, size=n, p=age_probs)

    # --- Gender ---
    genders = list(cfg["gender"].keys())
    gender_probs = list(cfg["gender"].values())
    user_genders = rng.choice(genders, size=n, p=gender_probs)

    df = pd.DataFrame({
        "user_id": np.arange(1, n + 1),
        "signup_date": signup_dates.dt.date,
        "signup_timestamp": signup_timestamps,
        "acquisition_channel": acquisition,
        "country": user_countries,
        "device_primary": user_devices,
        "age_bucket": user_ages,
        "gender": user_genders,
    })

    return df
