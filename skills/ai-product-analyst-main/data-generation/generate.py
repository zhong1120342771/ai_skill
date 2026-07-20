#!/usr/bin/env python3
"""Main orchestrator for NovaMart dataset generation.

Runs all generators in dependency order, injects stories, exports CSVs,
creates DuckDB databases, and validates quality gates.

Usage:
    cd data-generation
    python generate.py
"""

import os
import sys
import time
import yaml
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from generators import calendar_gen, products, promotions, experiments, users
from generators import sessions_and_events, orders, memberships
from generators import support_tickets, nps_responses, experiment_assignments
from stories import ticket_spike, activation_drop, nps_paradox
from stories import power_user_fallacy, checkout_confound
from capstone.apply_landmines import apply_landmines
from export import export_csvs
from load_duckdb import create_database
from quality_gates import run_all


def main():
    t0 = time.time()

    # --- Load config ---
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    with open(config_path) as f:
        config = yaml.safe_load(f)

    seed = config["general"]["random_seed"]
    rng = np.random.default_rng(seed)

    # Resolve output directories relative to repo root
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    practice_dir = os.path.join(repo_root, config["general"]["practice_output_dir"])
    capstone_dir = os.path.join(repo_root, config["general"]["capstone_output_dir"])

    # =========================================================
    # PHASE 1: Dimension tables (no dependencies)
    # =========================================================
    print("\n[Phase 1] Generating dimension tables...")
    calendar_df = calendar_gen.generate(config)
    print(f"  calendar: {len(calendar_df)} rows")

    promotions_df = promotions.generate(config)
    print(f"  promotions: {len(promotions_df)} rows")

    experiments_df = experiments.generate(config)
    print(f"  experiments: {len(experiments_df)} rows")

    products_df = products.generate(config, rng)
    print(f"  products: {len(products_df)} rows")

    # =========================================================
    # PHASE 2: Users (depends on calendar)
    # =========================================================
    print("\n[Phase 2] Generating users...")
    users_df = users.generate(config, calendar_df, rng)
    print(f"  users: {len(users_df)} rows")

    # =========================================================
    # PHASE 3: Sessions & Events (the big one)
    # =========================================================
    print("\n[Phase 3] Generating sessions and events (this takes a while)...")
    sessions_df, events_df = sessions_and_events.generate(
        config, users_df, products_df, calendar_df, rng
    )

    # =========================================================
    # PHASE 4: Derived fact tables
    # =========================================================
    print("\n[Phase 4] Generating derived fact tables...")

    print("  Generating memberships...")
    memberships_df = memberships.generate(config, users_df, rng)

    print("  Generating orders...")
    orders_df, order_items_df = orders.generate(
        config, events_df, products_df, users_df, promotions_df, memberships_df, rng
    )

    print("  Generating support tickets...")
    support_tickets_df = support_tickets.generate(
        config, users_df, orders_df, calendar_df, config["app_versions"], rng
    )

    print("  Generating NPS responses...")
    nps_responses_df = nps_responses.generate(config, users_df, memberships_df, rng)

    print("  Generating experiment assignments...")
    exp_assignments_df = experiment_assignments.generate(
        config, users_df, experiments_df, rng
    )

    # =========================================================
    # PHASE 5: Story injection
    # =========================================================
    print("\n[Phase 5] Injecting analytical stories...")

    # Story 1: Ticket Spike
    support_tickets_df = ticket_spike.inject(
        support_tickets_df, users_df, config, rng
    )

    # Story 2: Activation Drop (validate — pattern should already exist)
    activation_drop.validate(users_df, orders_df, config)

    # Story 3: NPS Paradox (validate — pattern should already exist)
    nps_paradox.validate(nps_responses_df, config)

    # Story 4: Power User Fallacy
    events_df, orders_df, order_items_df = power_user_fallacy.inject(
        events_df, orders_df, order_items_df, exp_assignments_df,
        products_df, config, rng
    )

    # Story 5: Checkout Confound
    events_df, orders_df, order_items_df = checkout_confound.inject(
        events_df, orders_df, order_items_df, products_df, config, rng
    )

    # =========================================================
    # PHASE 6: Export practice dataset
    # =========================================================
    print("\n[Phase 6] Exporting practice dataset...")
    practice_tables = {
        "calendar": calendar_df,
        "users": users_df,
        "products": products_df,
        "promotions": promotions_df,
        "experiments": experiments_df,
        "events": events_df,
        "sessions": sessions_df,
        "orders": orders_df,
        "order_items": order_items_df,
        "memberships": memberships_df,
        "support_tickets": support_tickets_df,
        "nps_responses": nps_responses_df,
        "experiment_assignments": exp_assignments_df,
    }
    export_csvs(practice_tables, practice_dir)

    print("\n  Creating practice DuckDB database...")
    practice_db = os.path.join(practice_dir, "novamart_practice.duckdb")
    create_database(practice_dir, practice_db)

    # =========================================================
    # PHASE 7: Generate capstone dataset (apply landmines)
    # =========================================================
    print("\n[Phase 7] Creating capstone dataset (applying landmines)...")
    capstone_rng = np.random.default_rng(config["capstone"]["random_seed"])
    capstone_tables = apply_landmines(practice_tables, config, capstone_rng)

    export_csvs(capstone_tables, capstone_dir)

    print("\n  Creating capstone DuckDB database...")
    capstone_db = os.path.join(capstone_dir, "novamart_capstone.duckdb")
    create_database(capstone_dir, capstone_db)

    # =========================================================
    # PHASE 8: Quality gates
    # =========================================================
    print("\n[Phase 8] Running quality gates...")
    all_passed = run_all(practice_tables, capstone_tables)

    # =========================================================
    # Summary
    # =========================================================
    elapsed = time.time() - t0
    print(f"\n{'='*50}")
    print(f"  Generation complete in {elapsed:.1f}s")
    print(f"  Practice: {practice_dir}")
    print(f"  Capstone: {capstone_dir}")
    print(f"  All gates passed: {'YES' if all_passed else 'NO'}")
    print(f"{'='*50}")

    # Print table summary
    print("\n  Table sizes (practice):")
    for name, df in practice_tables.items():
        print(f"    {name:30s} {len(df):>10,} rows")

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
