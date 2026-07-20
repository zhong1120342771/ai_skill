"""Generate the calendar dimension table (366 rows for 2024 leap year)."""

import pandas as pd


HOLIDAYS = {
    "2024-01-01": "New Year's Day",
    "2024-02-19": "Presidents' Day",
    "2024-05-27": "Memorial Day",
    "2024-07-04": "Independence Day",
    "2024-09-02": "Labor Day",
    "2024-10-14": "Columbus Day",
    "2024-11-11": "Veterans Day",
    "2024-11-28": "Thanksgiving",
    "2024-11-29": "Black Friday",
    "2024-12-02": "Cyber Monday",
    "2024-12-24": "Christmas Eve",
    "2024-12-25": "Christmas",
    "2024-12-31": "New Year's Eve",
}


def generate(config: dict) -> pd.DataFrame:
    start, end = config["general"]["time_range"]
    dates = pd.date_range(start, end, freq="D")

    df = pd.DataFrame({"date": dates.date})
    df["day_of_week"] = dates.day_name()
    df["is_weekend"] = dates.weekday >= 5
    df["month"] = dates.month
    df["quarter"] = dates.quarter
    df["is_holiday"] = df["date"].astype(str).isin(HOLIDAYS)
    df["holiday_name"] = df["date"].astype(str).map(HOLIDAYS)

    return df
