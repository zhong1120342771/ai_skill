from __future__ import annotations

"""Post-generation quality gates for both practice and capstone datasets.

Each gate returns (passed: bool, message: str).
Run all gates and report pass/fail summary.
"""

import pandas as pd
import numpy as np


def _check(condition: bool, name: str, detail: str = "") -> tuple[bool, str]:
    status = "PASS" if condition else "FAIL"
    msg = f"  [{status}] {name}"
    if detail:
        msg += f" — {detail}"
    return condition, msg


def run_practice_gates(tables: dict[str, pd.DataFrame]) -> list[tuple[bool, str]]:
    """Run all quality gates for the practice dataset."""
    results = []

    # --- Row count gates ---
    count_gates = {
        "users": (49000, 51000),
        "products": (490, 510),
        "calendar": (365, 367),
        "promotions": (5, 5),
        "experiments": (2, 2),
        "events": (2_000_000, 8_000_000),
        "sessions": (200_000, 2_000_000),
        "orders": (15_000, 80_000),
        "order_items": (30_000, 200_000),
        "memberships": (3_000, 25_000),
        "support_tickets": (10_000, 50_000),
        "nps_responses": (6_000, 10_000),
        "experiment_assignments": (15_000, 25_000),
    }

    for table, (lo, hi) in count_gates.items():
        if table not in tables:
            results.append(_check(False, f"{table} row count", "TABLE MISSING"))
            continue
        n = len(tables[table])
        passed = lo <= n <= hi
        results.append(_check(passed, f"{table} row count", f"{n:,} (expected {lo:,}-{hi:,})"))

    # --- Referential integrity ---
    if "events" in tables and "users" in tables:
        user_ids = set(tables["users"]["user_id"])
        event_users = set(tables["events"]["user_id"].unique())
        orphans = event_users - user_ids
        results.append(_check(len(orphans) == 0, "events→users FK",
                             f"{len(orphans)} orphan user_ids"))

    if "orders" in tables and "users" in tables:
        user_ids = set(tables["users"]["user_id"])
        order_users = set(tables["orders"]["user_id"].unique())
        orphans = order_users - user_ids
        results.append(_check(len(orphans) == 0, "orders→users FK",
                             f"{len(orphans)} orphan user_ids"))

    if "order_items" in tables and "orders" in tables:
        order_ids = set(tables["orders"]["order_id"])
        item_orders = set(tables["order_items"]["order_id"].unique())
        orphans = item_orders - order_ids
        results.append(_check(len(orphans) == 0, "order_items→orders FK",
                             f"{len(orphans)} orphan order_ids"))

    if "support_tickets" in tables and "users" in tables:
        user_ids = set(tables["users"]["user_id"])
        ticket_users = set(tables["support_tickets"]["user_id"].unique())
        orphans = ticket_users - user_ids
        results.append(_check(len(orphans) == 0, "support_tickets→users FK",
                             f"{len(orphans)} orphan user_ids"))

    if "nps_responses" in tables and "users" in tables:
        user_ids = set(tables["users"]["user_id"])
        nps_users = set(tables["nps_responses"]["user_id"].unique())
        orphans = nps_users - user_ids
        results.append(_check(len(orphans) == 0, "nps_responses→users FK",
                             f"{len(orphans)} orphan user_ids"))

    # --- Funnel rates ---
    if "events" in tables:
        events = tables["events"]
        event_counts = events["event_type"].value_counts()

        pv = event_counts.get("product_view", 0)
        atc = event_counts.get("add_to_cart", 0)
        cs = event_counts.get("checkout_started", 0)
        pa = event_counts.get("payment_attempted", 0)
        pc = event_counts.get("purchase_complete", 0)

        if pv > 0:
            atc_rate = atc / pv
            results.append(_check(0.10 <= atc_rate <= 0.40,
                                 "product_view→add_to_cart rate",
                                 f"{atc_rate:.3f}"))
        if atc > 0:
            cs_rate = cs / atc
            results.append(_check(0.30 <= cs_rate <= 0.80,
                                 "add_to_cart→checkout rate",
                                 f"{cs_rate:.3f}"))
        if cs > 0:
            pa_rate = pa / cs
            results.append(_check(0.40 <= pa_rate <= 1.0,
                                 "checkout→payment rate",
                                 f"{pa_rate:.3f}"))
        if pa > 0:
            pc_rate = pc / pa
            results.append(_check(0.50 <= pc_rate <= 1.0,
                                 "payment→purchase rate",
                                 f"{pc_rate:.3f}"))

    # --- Story verification ---
    # Story 1: Ticket Spike
    if "support_tickets" in tables:
        tickets = tables["support_tickets"]
        tickets_dt = tickets.copy()
        tickets_dt["created_date"] = pd.to_datetime(tickets_dt["created_date"])

        spike_tickets = tickets_dt[
            (tickets_dt["created_date"] >= "2024-06-01") &
            (tickets_dt["created_date"] <= "2024-06-14") &
            (tickets_dt["category"] == "payment_issue")
        ]
        non_spike_tickets = tickets_dt[
            (tickets_dt["category"] == "payment_issue") &
            ~((tickets_dt["created_date"] >= "2024-06-01") &
              (tickets_dt["created_date"] <= "2024-06-14"))
        ]
        spike_daily = len(spike_tickets) / 14
        non_spike_days = max(1, 365 - 14)
        baseline_daily = len(non_spike_tickets) / non_spike_days
        ratio = spike_daily / max(1, baseline_daily)
        results.append(_check(ratio > 2.0, "Story 1: Ticket spike ratio",
                             f"{ratio:.1f}x (need >2.0x)"))

    # Story 3: NPS Paradox
    if "nps_responses" in tables and "user_segment" in tables["nps_responses"].columns:
        nps = tables["nps_responses"].copy()
        nps["response_date"] = pd.to_datetime(nps["response_date"])
        nps["quarter"] = nps["response_date"].dt.quarter

        def calc_nps(scores):
            n = len(scores)
            if n == 0:
                return 0
            return round(((scores >= 9).sum() - (scores <= 6).sum()) / n * 100, 1)

        q1_agg = calc_nps(nps[nps["quarter"] == 1]["score"])
        q2_agg = calc_nps(nps[nps["quarter"] == 2]["score"])
        q1_free = calc_nps(nps[(nps["quarter"] == 1) & (nps["user_segment"] == "free")]["score"])
        q2_free = calc_nps(nps[(nps["quarter"] == 2) & (nps["user_segment"] == "free")]["score"])
        q1_plus = calc_nps(nps[(nps["quarter"] == 1) & (nps["user_segment"] == "plus")]["score"])
        q2_plus = calc_nps(nps[(nps["quarter"] == 2) & (nps["user_segment"] == "plus")]["score"])

        agg_dropped = q2_agg < q1_agg
        both_improved = q2_free >= q1_free and q2_plus >= q1_plus
        results.append(_check(agg_dropped and both_improved,
                             "Story 3: NPS Simpson's Paradox",
                             f"agg Q1={q1_agg} Q2={q2_agg}, "
                             f"free Q1={q1_free} Q2={q2_free}, "
                             f"plus Q1={q1_plus} Q2={q2_plus}"))

    # Story 6: Mobile checkout gap
    if "events" in tables:
        events = tables["events"]
        mobile_events = events[events["device"].isin(["ios", "android"])]
        desktop_events = events[events["device"] == "web"]

        mobile_cs = (mobile_events["event_type"] == "checkout_started").sum()
        mobile_pc = (mobile_events["event_type"] == "purchase_complete").sum()
        desktop_cs = (desktop_events["event_type"] == "checkout_started").sum()
        desktop_pc = (desktop_events["event_type"] == "purchase_complete").sum()

        mobile_cvr = mobile_pc / max(1, mobile_cs)
        desktop_cvr = desktop_pc / max(1, desktop_cs)
        gap = desktop_cvr - mobile_cvr

        results.append(_check(gap >= 0.02, "Story 6: Mobile checkout gap",
                             f"mobile={mobile_cvr:.3f}, desktop={desktop_cvr:.3f}, gap={gap:.3f}"))

    # --- Time completeness ---
    if "events" in tables:
        events = tables["events"]
        event_dates = pd.to_datetime(events["event_date"]).dt.date
        unique_dates = set(event_dates)
        all_dates = set(pd.date_range("2024-01-01", "2024-12-31").date)
        missing = all_dates - unique_dates
        results.append(_check(len(missing) == 0, "Time completeness",
                             f"{len(missing)} dates missing events"))

    # --- No null PKs ---
    pk_columns = {
        "users": "user_id", "products": "product_id", "orders": "order_id",
        "order_items": "order_item_id", "support_tickets": "ticket_id",
        "nps_responses": "response_id", "experiment_assignments": "assignment_id",
    }
    for table, pk in pk_columns.items():
        if table in tables and pk in tables[table].columns:
            nulls = tables[table][pk].isna().sum()
            results.append(_check(nulls == 0, f"{table}.{pk} no nulls",
                                 f"{nulls} null PKs"))

    return results


def run_capstone_gates(tables: dict[str, pd.DataFrame]) -> list[tuple[bool, str]]:
    """Run capstone-specific quality gates."""
    results = []

    # Duplicates exist
    if "events" in tables:
        events = tables["events"]
        dupes = events.duplicated(subset=["event_id"], keep=False).sum()
        results.append(_check(dupes > 0, "Capstone: duplicate events exist",
                             f"{dupes:,} duplicate rows"))

    # No sessions table
    results.append(_check("sessions" not in tables, "Capstone: no sessions table"))

    # No user_segment in nps
    if "nps_responses" in tables:
        has_segment = "user_segment" in tables["nps_responses"].columns
        results.append(_check(not has_segment, "Capstone: no user_segment in nps"))

    # Device nulls in support tickets
    if "support_tickets" in tables:
        null_pct = tables["support_tickets"]["device"].isna().mean()
        results.append(_check(null_pct >= 0.25,
                             "Capstone: support ticket device nulls",
                             f"{null_pct:.1%} null"))

    # Orphan orders
    if "orders" in tables and "users" in tables:
        user_ids = set(tables["users"]["user_id"])
        order_users = set(tables["orders"]["user_id"].unique())
        orphans = order_users - user_ids
        results.append(_check(len(orphans) > 0,
                             "Capstone: orphan orders exist",
                             f"{len(orphans)} orphan user_ids"))

    return results


def run_all(practice_tables: dict, capstone_tables: dict) -> bool:
    """Run all gates and print summary. Returns True if all pass."""
    print("\n=== Practice Dataset Quality Gates ===")
    practice_results = run_practice_gates(practice_tables)

    print("\n=== Capstone Dataset Quality Gates ===")
    capstone_results = run_capstone_gates(capstone_tables)

    all_results = practice_results + capstone_results
    for passed, msg in all_results:
        print(msg)

    n_passed = sum(1 for p, _ in all_results if p)
    n_total = len(all_results)
    n_failed = n_total - n_passed

    print(f"\n{'='*50}")
    print(f"  {n_passed}/{n_total} gates passed, {n_failed} failed")
    print(f"{'='*50}")

    return n_failed == 0
