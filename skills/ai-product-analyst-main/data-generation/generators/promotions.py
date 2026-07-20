"""Generate the promotions dimension table (5 rows)."""

import pandas as pd


def generate(config: dict) -> pd.DataFrame:
    rows = []
    for p in config["promotions"]:
        rows.append({
            "promo_id": p["promo_id"],
            "promo_name": p["name"],
            "promo_type": p["type"],
            "discount_pct": p["discount"],
            "start_date": pd.Timestamp(p["start"]).date(),
            "end_date": pd.Timestamp(p["end"]).date(),
            "target_segment": p["target"],
        })
    return pd.DataFrame(rows)
