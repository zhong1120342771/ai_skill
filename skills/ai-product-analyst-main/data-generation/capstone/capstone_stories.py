"""Generate capstone-specific analytical stories.

The capstone uses the same base data generation but with a different seed
and year (2023).  The stories are different from practice:

1. Simpson's Paradox (different): Overall conversion drops but every channel improves.
   Caused by paid budget cut shifting mix toward lower-converting organic.
2. Selection Bias (different): Push notification users have 2x retention,
   but experiment shows only 12% lift.
3. Seasonality Trap: Naive Dec→Jan comparison shows "decline" but it's just
   seasonality.
4. Confounding (different): Price drop + UI change same week.  Mobile-only
   UI change allows separation.

For the capstone, these stories are baked into the base generation via
the different seed.  This module documents them but doesn't modify data
beyond what the generators produce, since the capstone data uses a
different seed that naturally produces different patterns.
"""


def describe_stories() -> dict:
    """Return documentation of capstone stories for quality gate validation."""
    return {
        "simpsons_paradox": {
            "description": "Overall conversion drops Q2→Q3, but within each channel it rose",
            "cause": "Paid budget cut shifted mix toward lower-converting organic",
            "detection": "Segment conversion by acquisition_channel",
        },
        "selection_bias": {
            "description": "Push notification users have 2x retention",
            "cause": "Engaged users self-select into enabling notifications",
            "true_effect": "12% relative lift in experiment",
        },
        "seasonality_trap": {
            "description": "Naive Dec→Jan shows decline",
            "cause": "Holiday seasonality, not actual decline",
            "detection": "Compare same months YoY or deseasonalize",
        },
        "confounding": {
            "description": "Price drop + UI change in same week",
            "cause": "UI change is mobile-only, price drop is universal",
            "detection": "Segment by device to isolate UI effect",
        },
    }
