"""Generate the nps_responses table (~8K rows).

NPS score distribution is calibrated to hit target NPS values:
  - Free users: NPS ~28 (Q1), ~30 (Q2)
  - Plus users: NPS ~52 (Q1), ~54 (Q2)

NPS = %Promoters(9-10) - %Detractors(0-6), on a -100 to +100 scale.

To generate scores that produce a target NPS, we control the mix of
detractors/passives/promoters and then sample individual scores within
each bucket.
"""

import numpy as np
import pandas as pd


def _nps_to_bucket_probs(target_nps: float) -> dict:
    """Convert a target NPS (-100 to 100) to promoter/passive/detractor percentages.

    We set detractor% = (1 - target_nps/100) / 3 approximately, then adjust.
    NPS = promoter% - detractor%.
    promoter% + passive% + detractor% = 1.
    """
    # target_nps = (promoter - detractor) * 100
    # promoter + passive + detractor = 1
    # Set passive to ~25% and solve for promoter/detractor
    target_frac = target_nps / 100.0  # e.g. 0.28
    passive = 0.25
    # promoter - detractor = target_frac
    # promoter + detractor = 1 - passive = 0.75
    # promoter = (0.75 + target_frac) / 2
    # detractor = (0.75 - target_frac) / 2
    promoter = (1 - passive + target_frac) / 2
    detractor = (1 - passive - target_frac) / 2

    # Clamp
    promoter = max(0.05, min(0.90, promoter))
    detractor = max(0.05, min(0.90, detractor))
    passive = 1.0 - promoter - detractor
    if passive < 0:
        passive = 0.05
        total = promoter + detractor + passive
        promoter /= total
        detractor /= total
        passive /= total

    return {"promoter": promoter, "passive": passive, "detractor": detractor}


def _sample_scores(n: int, target_nps: float, rng: np.random.Generator) -> np.ndarray:
    """Sample n NPS scores (0-10) that produce approximately the target NPS."""
    buckets = _nps_to_bucket_probs(target_nps)

    n_promoter = int(n * buckets["promoter"])
    n_detractor = int(n * buckets["detractor"])
    n_passive = n - n_promoter - n_detractor

    scores = np.concatenate([
        rng.choice([9, 10], size=n_promoter, p=[0.45, 0.55]),      # promoters
        rng.choice([7, 8], size=n_passive, p=[0.50, 0.50]),          # passives
        rng.choice([0, 1, 2, 3, 4, 5, 6], size=n_detractor,
                   p=[0.02, 0.03, 0.05, 0.08, 0.12, 0.30, 0.40]),  # detractors
    ])
    rng.shuffle(scores)
    return scores


NPS_COMMENTS = [
    "Great service, fast delivery!",
    "Love the product selection.",
    "Prices are reasonable.",
    "Easy to use website.",
    "Customer support was helpful.",
    "Shipping was slow this time.",
    "Had trouble with payment.",
    "Product quality could be better.",
    "Would recommend to friends.",
    "App keeps crashing.",
    "Return process was smooth.",
    "Too many emails from NovaMart.",
    "Membership is worth it.",
    "Not sure I'll renew my Plus membership.",
    "Found exactly what I needed.",
    "Checkout process is confusing on mobile.",
    "Great deals during sales.",
    "Product didn't match description.",
    "Delivery was on time.",
    "Need more payment options.",
]


def generate(
    config: dict,
    users_df: pd.DataFrame,
    memberships_df: pd.DataFrame,
    rng: np.random.Generator,
) -> pd.DataFrame:
    cfg = config["nps"]
    responses_per_q = cfg["responses_per_quarter"]
    comment_rate = cfg["comment_rate"]

    # NPS responses are generated with denormalized user_segment.
    # The Free/Plus split is controlled by config, not by actual membership status.
    # This ensures the Simpson's Paradox story works regardless of membership counts.

    # Quarter configs
    quarters = [
        {"q": 1, "start": "2024-01-01", "end": "2024-03-31",
         "free_pct": cfg["q1_free_response_pct"],
         "free_nps": cfg["free_nps_q1"], "plus_nps": cfg["plus_nps_q1"]},
        {"q": 2, "start": "2024-04-01", "end": "2024-06-30",
         "free_pct": cfg["q2_free_response_pct"],
         "free_nps": cfg["free_nps_q2"], "plus_nps": cfg["plus_nps_q2"]},
        {"q": 3, "start": "2024-07-01", "end": "2024-09-30",
         "free_pct": cfg["q3_free_response_pct"],
         "free_nps": (cfg["free_nps_q2"] + 1), "plus_nps": (cfg["plus_nps_q2"] + 1)},
        {"q": 4, "start": "2024-10-01", "end": "2024-12-31",
         "free_pct": cfg["q4_free_response_pct"],
         "free_nps": (cfg["free_nps_q2"] + 2), "plus_nps": (cfg["plus_nps_q2"] + 2)},
    ]

    all_user_ids = users_df["user_id"].values
    signup_dates = pd.to_datetime(users_df["signup_date"])

    rows = []
    response_id = 0
    devices = ["web", "ios", "android"]
    device_probs = [0.40, 0.35, 0.25]

    for qcfg in quarters:
        q_start = pd.Timestamp(qcfg["start"])
        q_end = pd.Timestamp(qcfg["end"])
        n_responses = responses_per_q

        # Users eligible: signed up before end of quarter
        eligible_mask = signup_dates <= q_end
        eligible_ids = all_user_ids[eligible_mask]
        if len(eligible_ids) == 0:
            continue

        # Split into free and plus based on configured percentages
        # (not actual membership status — user_segment is denormalized for the story)
        n_free = int(n_responses * qcfg["free_pct"])
        n_plus = n_responses - n_free

        # Randomly sample respondents (allow replacement if needed)
        respondents = rng.choice(eligible_ids, size=n_responses, replace=False)
        free_respondents = respondents[:n_free]
        plus_respondents = respondents[n_free:]

        # Generate scores
        free_scores = _sample_scores(n_free, qcfg["free_nps"], rng) if n_free > 0 else np.array([])
        plus_scores = _sample_scores(n_plus, qcfg["plus_nps"], rng) if n_plus > 0 else np.array([])

        # Random dates within quarter
        q_days = (q_end - q_start).days + 1

        for uid, score in zip(free_respondents, free_scores):
            response_id += 1
            resp_date = q_start + pd.Timedelta(days=int(rng.integers(0, q_days)))
            comment = rng.choice(NPS_COMMENTS) if rng.random() < comment_rate else None
            rows.append({
                "response_id": response_id,
                "user_id": int(uid),
                "response_date": resp_date.date(),
                "score": int(score),
                "user_segment": "free",
                "device": rng.choice(devices, p=device_probs),
                "comment": comment,
            })

        for uid, score in zip(plus_respondents, plus_scores):
            response_id += 1
            resp_date = q_start + pd.Timedelta(days=int(rng.integers(0, q_days)))
            comment = rng.choice(NPS_COMMENTS) if rng.random() < comment_rate else None
            rows.append({
                "response_id": response_id,
                "user_id": int(uid),
                "response_date": resp_date.date(),
                "score": int(score),
                "user_segment": "plus",
                "device": rng.choice(devices, p=device_probs),
                "comment": comment,
            })

    df = pd.DataFrame(rows)
    print(f"  Generated {len(df):,} NPS responses")
    return df
