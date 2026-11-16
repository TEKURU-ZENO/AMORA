"""Execute the Conversational Evaluation Study with Live LLM (Ollama) and Label Engine."""
from __future__ import annotations

import json
import os
import sys
import time

# Ensure Ollama and calibrated date turns are active
os.environ["USE_OLLAMA"] = "1"
os.environ.setdefault("OLLAMA_MODEL", "llama3.2:1b")
os.environ.setdefault("DATE_TURNS", "4")

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, store
from app.evaluation.conversational_eval import (
    render_evaluation_comparison_svg,
    run_conversational_study,
)


def main():
    store.init()
    print("=" * 70)
    print("AMORA CONVERSATIONAL STUDY RUNNER (LIVE LLM ENABLED)")
    print("=" * 70)
    print(f"Provider:           {config.llm_provider()}")
    print(f"Engine Model:       {config.active_model_name()}")
    print(f"Date Turns:         {config.DATE_TURNS}")
    print(f"Ollama Host:        {config.OLLAMA_HOST}")
    print(f"Ollama Available:   {config.ollama_available()}")
    print("-" * 70)

    t0 = time.time()
    study = run_conversational_study()
    t1 = time.time()

    print("\n" + "=" * 70)
    print("EMPIRICAL STUDY RESULTS")
    print("=" * 70)
    print(f"Headline: {study['headline']}")
    print(f"Engine Labeled: {study['engine']}")
    print(f"LLM Enabled: {study['llm_enabled']}")
    print(f"Execution Duration: {round(t1 - t0, 2)}s")

    metrics = study["metrics"]
    print("\nAggregated Metrics:")
    for k, v in metrics.items():
        print(f"  {k:30s}: {v}")

    print("\nPair-by-Pair Breakdown:")
    for idx, p in enumerate(study["pairs"], 1):
        print(f"\n--- Case {idx}: {p['name_a']} & {p['name_b']} [{p['pair_id']}] ---")
        print(f"  Public Overlap:   {p['public_overlap_summary']}")
        print(f"  Hidden Signal:    {p['hidden_conversational_facts']}")
        print(f"  Ground Truth y*:  {p['ground_truth_score']:.1f}")
        print(f"  Profile Prior y0: {p['baseline_prior_score']:.1f} (Err: {p['error_prior']:.1f})")
        print(f"  Agent Date y_llm: {p['agent_verdict_score']:.1f} (Err: {p['error_agent']:.1f})")
        print(f"  Error Reduction:  {p['error_reduction']:.1f} points ({'AGENT WON' if p['agent_won'] else 'PRIOR CLOSER'})")
        print(f"  Date Engine:      {p['engine']}")

    svg = render_evaluation_comparison_svg(study)
    out_dir = config.DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "conversational_study_llm.json"
    svg_path = out_dir / "conversational_study_llm.svg"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(study, f, indent=2)
    with open(svg_path, "w", encoding="utf-8") as f:
        f.write(svg)

    print("\n" + "=" * 70)
    print(f"Artifacts saved:")
    print(f"  JSON: {json_path}")
    print(f"  SVG:  {svg_path}")
    print("=" * 70)


if __name__ == "__main__":
    main()
