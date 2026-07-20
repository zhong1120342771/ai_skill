from __future__ import annotations

"""Export DataFrames to CSV files in a target directory."""

import os
import pandas as pd


def export_csvs(tables: dict[str, pd.DataFrame], output_dir: str) -> None:
    """Write each DataFrame to a CSV file in output_dir.

    Args:
        tables: dict mapping table name to DataFrame
        output_dir: directory to write CSVs into
    """
    os.makedirs(output_dir, exist_ok=True)

    for name, df in tables.items():
        path = os.path.join(output_dir, f"{name}.csv")
        df.to_csv(path, index=False)
        print(f"  Exported {name}.csv ({len(df):,} rows)")
