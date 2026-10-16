"""Add opted-in people to the pool (scraped live through Apify), then run a dating round.

  python -m scripts.seed --csv optins.csv

The CSV needs columns: linkedin,instagram,consent  (consent must be "yes" for every row,
collected from the person themselves, e.g. via the /join form or a signup sheet).
"""
from __future__ import annotations

import argparse
import csv
import sys

from app import config, harness, store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", required=True, help="columns: linkedin,instagram,consent")
    ap.add_argument("--no-round", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    store.init()
    if args.reset:
        for p in store.list_persons():
            store.delete_person(p.id)
    if not config.scraping_enabled():
        sys.exit("APIFY_TOKEN is not set. The pool is built only from live Apify scrapes.")
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
