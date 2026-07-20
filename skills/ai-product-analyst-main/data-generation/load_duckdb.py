"""Create a DuckDB database from CSV files in a directory."""

import os
import glob
import duckdb


def create_database(csv_dir: str, db_path: str) -> None:
    """Load all CSVs from csv_dir into a DuckDB database at db_path."""
    if os.path.exists(db_path):
        os.remove(db_path)

    con = duckdb.connect(db_path)

    csv_files = sorted(glob.glob(os.path.join(csv_dir, "*.csv")))

    for csv_path in csv_files:
        table_name = os.path.splitext(os.path.basename(csv_path))[0]
        con.execute(f"""
            CREATE TABLE {table_name} AS
            SELECT * FROM read_csv_auto('{csv_path}')
        """)
        count = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        print(f"  Loaded {table_name} into DuckDB ({count:,} rows)")

    # Show all tables
    tables = con.execute("SHOW TABLES").fetchall()
    print(f"  DuckDB database created at {db_path} with {len(tables)} tables")

    con.close()
