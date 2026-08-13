"""
run_queries.py
---------------
Runs every query in queries.sql against op_risk.db and prints the results.
No GUI extension needed -- just run: python3 run_queries.py
"""

import sqlite3
import re

DB_PATH = "op_risk.db"
QUERIES_PATH = "queries.sql"


def load_queries(path):
    with open(path) as f:
        lines = f.readlines()

    queries = []
    current = []
    label = None
    for line in lines:
        if re.match(r"^-- \d+\.", line):
            if current and label:
                queries.append((label, "".join(current)))
            label = line.strip()
            current = []
        else:
            current.append(line)
    if current and label:
        queries.append((label, "".join(current)))
    return queries


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    queries = load_queries(QUERIES_PATH)

    for label, block in queries:
        sql_lines = [l for l in block.splitlines() if not l.strip().startswith("--")]
        sql = "\n".join(sql_lines).strip()

        print("=" * 70)
        print(label)
        print("=" * 70)

        try:
            cur.execute(sql)
            rows = cur.fetchall()
            cols = [d[0] for d in cur.description]
            print(" | ".join(cols))
            for row in rows[:10]:
                print(" | ".join(str(v) for v in row))
            if len(rows) > 10:
                print(f"... and {len(rows) - 10} more rows")
            print(f"\n({len(rows)} rows total)\n")
        except Exception as e:
            print("ERROR running this query:", e, "\n")

    conn.close()


if __name__ == "__main__":
    main()
