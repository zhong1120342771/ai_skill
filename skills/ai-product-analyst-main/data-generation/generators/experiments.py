"""Generate the experiments dimension table (2 rows)."""

import pandas as pd


def generate(config: dict) -> pd.DataFrame:
    rows = []
    for e in config["experiments"]:
        rows.append({
            "experiment_id": e["experiment_id"],
            "experiment_name": e["experiment_name"],
            "hypothesis": e["hypothesis"],
            "primary_metric": e["primary_metric"],
            "guardrail_metrics": e["guardrail_metrics"],
            "start_date": pd.Timestamp(e["start_date"]).date(),
            "end_date": pd.Timestamp(e["end_date"]).date(),
            "status": e["status"],
        })
    return pd.DataFrame(rows)
