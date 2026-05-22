"""Aperçu rapide de la base SQLite. Usage : python tools/dump_db.py"""
import os
import sys
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config


def dump_table(c, name, limit=20):
    print(f"\n=== {name} (max {limit} lignes) ===")
    rows = list(c.execute(f"SELECT * FROM {name} LIMIT {limit}"))
    if not rows:
        print("  (vide)")
        return
    cols = [d[0] for d in c.execute(f"SELECT * FROM {name} LIMIT 0").description]
    for r in rows:
        print("  " + " | ".join(f"{cols[i]}={v}" for i, v in enumerate(r)))


def main():
    c = sqlite3.connect(config.DB_PATH)
    print(f"DB : {config.DB_PATH}")
    for t, lim in (("result", 30), ("stats", 10),
                   ("soft_bounce_counter", 30), ("counters", 5),
                   ("rule_suggestions", 20)):
        try:
            dump_table(c, t, lim)
        except sqlite3.OperationalError as e:
            print(f"\n=== {t} ===\n  (table absente : {e})")
    # Totaux par catégorie
    print("\n=== Totaux par catégorie (table result) ===")
    for cat, n in c.execute(
        "SELECT category, COUNT(*) FROM result GROUP BY category ORDER BY 2 DESC"
    ):
        print(f"  {cat:20s} : {n}")
    c.close()


if __name__ == "__main__":
    main()
