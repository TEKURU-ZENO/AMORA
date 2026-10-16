"""Add people to the pool, then run a dating round.

  python -m scripts.seed --csv optins.csv      # opted-in people, scraped live through Apify
  python -m scripts.seed --synthetic           # 25 fictional personas; needs AGENTDATE_DEMO=1

The CSV needs columns: linkedin,instagram,consent  (consent must be "yes" for every row,
collected from the person themselves, e.g. via the /join form or a signup sheet).
"""
from __future__ import annotations

import argparse
import os
import csv
import sys

from app import config, harness, store


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", help="columns: linkedin,instagram,consent")
    ap.add_argument("--synthetic", action="store_true", help="fictional demo personas (demo mode only)")
    ap.add_argument("--no-round", action="store_true")
    ap.add_argument("--reset", action="store_true")
    args = ap.parse_args()
    store.init()
    if args.reset:
        for p in store.list_persons():
            store.delete_person(p.id)
    if not (args.csv or args.synthetic):
        sys.exit("Pass --csv optins.csv and/or --synthetic.")
    if args.synthetic:
        if not config.demo_mode():
            sys.exit("--synthetic needs demo mode: set AGENTDATE_DEMO=1 (e.g. in .env).")
        from scripts.synthetic import build
        for pid, li, ig in build():
            harness.ingest_demo(pid, li, ig)
    if args.csv and not config.scraping_enabled():
        sys.exit("APIFY_TOKEN is not set. Real people are added only through live Apify scrapes.")
    with open(args.csv) if args.csv else open(os.devnull) as f:
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
