"""Story 3: NPS Simpson's Paradox.

The NPS generator (nps_responses.py) already controls the Free/Plus mix
per quarter and score distributions.  This script validates the pattern
and reports diagnostics.
"""

import pandas as pd
import numpy as np


def validate(nps_df: pd.DataFrame, config: dict) -> dict:
    """Validate that Story 3 pattern is present."""
    df = nps_df.copy()
    df["response_date"] = pd.to_datetime(df["response_date"])
    df["quarter"] = df["response_date"].dt.quarter

    # Calculate NPS per quarter per segment
    def calc_nps(scores):
        n = len(scores)
        if n == 0:
            return 0
        promoters = (scores >= 9).sum() / n * 100
        detractors = (scores <= 6).sum() / n * 100
        return round(promoters - detractors, 1)

    results = {}
    for q in [1, 2, 3, 4]:
        q_data = df[df["quarter"] == q]
        if len(q_data) == 0:
            continue
        free_data = q_data[q_data["user_segment"] == "free"]
        plus_data = q_data[q_data["user_segment"] == "plus"]

        free_nps = calc_nps(free_data["score"])
        plus_nps = calc_nps(plus_data["score"])
        agg_nps = calc_nps(q_data["score"])

        results[f"Q{q}"] = {
            "free_nps": free_nps,
            "plus_nps": plus_nps,
            "aggregate_nps": agg_nps,
            "free_count": len(free_data),
            "plus_count": len(plus_data),
            "free_pct": round(len(free_data) / max(1, len(q_data)) * 100, 1),
        }

    # Check paradox: Q2 aggregate < Q1 aggregate, but both segments improved
    q1 = results.get("Q1", {})
    q2 = results.get("Q2", {})

    paradox_present = (
        q2.get("aggregate_nps", 0) < q1.get("aggregate_nps", 0) and
        q2.get("free_nps", 0) >= q1.get("free_nps", 0) and
        q2.get("plus_nps", 0) >= q1.get("plus_nps", 0)
    )

    print(f"  Story 3 (NPS Paradox): "
          f"Q1 agg={q1.get('aggregate_nps')}, Q2 agg={q2.get('aggregate_nps')}, "
          f"Q1 free={q1.get('free_nps')}, Q2 free={q2.get('free_nps')}, "
          f"Q1 plus={q1.get('plus_nps')}, Q2 plus={q2.get('plus_nps')}, "
          f"paradox={'YES' if paradox_present else 'NO'}")

    return {"quarters": results, "paradox_present": paradox_present}
