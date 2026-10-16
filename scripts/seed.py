"""Seed the pool and run a dating round.

  python -m scripts.seed --synthetic           # 25 fictional test personas, no network
  python -m scripts.seed --csv optins.csv      # real people who opted in (live Apify scrape)

The CSV needs columns: linkedin,instagram,consent  (consent must be "yes" for every row,
collected from the person themselves, e.g. via the /join form or a signup sheet).
"""
from __future__ import annotations

import argparse
import csv
import sys

from app import harness, store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--synthetic", action="store_true")
    ap.add_argument("--csv")
    ap.add_argument("--no-round", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    store.init()
    if args.reset:
        for p in store.list_persons():
            store.delete_person(p.id)
    if args.synthetic:
        from scripts.synthetic import build
        for pid, li, ig in build():
            harness.ingest_sources(pid, li, ig, synthetic=True)
    if args.csv:
        with open(args.csv) as f:
            for row in csv.DictReader(f):
                if row.get("consent", "").strip().lower() != "yes":
                    print(f"skip (no consent): {row.get('linkedin')}", file=sys.stderr)
                    continue
                try:
                    harness.ingest(row["linkedin"], row["instagram"], consent=True)
                except Exception as e:
                    print(f"failed {row['linkedin']}: {e}", file=sys.stderr)
    if not args.no_round:
        harness.run_round()


if __name__ == "__main__":
    main()
