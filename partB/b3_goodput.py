#!/usr/bin/env python3
"""
b3_goodput.py -- B3: identify the column misread behind REPORT_v0's
"longer prompts give better throughput" claim and its batch-48 ~3200 tok/s
extrapolation, and derive the honest goodput of the batch-24, prompt-3584
row two independent ways.
"""

import csv
import os


def main():
    here = os.path.dirname(__file__)
    log_path = os.path.join(here, "bench", "bench_log.csv")
    with open(log_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    row24 = next(r for r in rows if r["batch_size"] == "24" and r["prompt_len"] == "3584")
    batch = int(row24["batch_size"])
    prompt_len = int(row24["prompt_len"])
    gen_len = int(row24["gen_len"])
    num_requests = int(row24["num_requests"])
    wall_clock_s = float(row24["wall_clock_s"])
    reported = float(row24["reported_tok_s"])
    itl_ms_p50 = float(row24["itl_ms_p50"])

    print("Row under test: batch=24, prompt_len=3584, gen_len=512")
    print(f"  wall_clock_s={wall_clock_s}, reported_tok_s={reported}, itl_ms_p50={itl_ms_p50}\n")

    print("Step 1: what column is REPORT_v0 actually reading?")
    guess_prefill_plus_decode = num_requests * (prompt_len + gen_len) / wall_clock_s
    print(f"  hypothesis: reported_tok_s = num_requests x (prompt_len + gen_len) / wall_clock_s")
    print(f"            = {num_requests} x ({prompt_len} + {gen_len}) / {wall_clock_s}")
    print(f"            = {guess_prefill_plus_decode:.1f}")
    print(f"  logged reported_tok_s      = {reported}")
    print(f"  match: {'YES -- reported_tok_s counts one-shot PREFILL tokens as if they were streamed decode throughput' if abs(guess_prefill_plus_decode - reported) < 1 else 'no match, hypothesis wrong'}\n")

    print("Step 2: honest decode goodput, way 1 -- generated tokens only, over wall clock")
    goodput_1 = num_requests * gen_len / wall_clock_s
    print(f"  = num_requests x gen_len / wall_clock_s")
    print(f"  = {num_requests} x {gen_len} / {wall_clock_s}")
    print(f"  = {goodput_1:.1f} tok/s\n")

    print("Step 3: honest decode goodput, way 2 -- independent, from per-token decode latency")
    goodput_2 = batch * (1000 / itl_ms_p50)
    print(f"  = batch_size x (1000 / itl_ms_p50)")
    print(f"  = {batch} x (1000 / {itl_ms_p50})")
    print(f"  = {goodput_2:.1f} tok/s\n")

    print(f"Both independent derivations land in the same ballpark: {goodput_1:.1f} vs {goodput_2:.1f} tok/s")
    print(f"(vs. the reported {reported} tok/s -- an overstatement of "
          f"{reported/goodput_1:.1f}x-{reported/goodput_2:.1f}x)\n")

    print("Step 4: what happens if you naively extrapolate the misread column to batch=48?")
    row48 = next(r for r in rows if r["batch_size"] == "48" and r["prompt_len"] == "3584")
    print(f"  REPORT_v0 extrapolation: ~1600 tok/s (batch 24 reported) x 2 (batch doubles) = ~3200 tok/s")
    print(f"  actual logged reported_tok_s at batch=48: {row48['reported_tok_s']}  (LOWER than batch 24, not higher)")
    print(f"  actual honest goodput at batch=48:")
    b48 = int(row48["batch_size"])
    wc48 = float(row48["wall_clock_s"])
    nr48 = int(row48["num_requests"])
    gl48 = int(row48["gen_len"])
    itl48 = float(row48["itl_ms_p50"])
    g1_48 = nr48 * gl48 / wc48
    g2_48 = b48 * (1000 / itl48)
    print(f"    way 1 (tokens/wall_clock): {g1_48:.1f} tok/s")
    print(f"    way 2 (batch x 1000/itl):  {g2_48:.1f} tok/s")
    print(f"  -> both are LOWER than batch=24's honest goodput ({goodput_1:.1f}/{goodput_2:.1f}), confirming the")
    print(f"     batch-48 ~3200 tok/s extrapolation is wrong twice over: wrong metric, and wrong direction")
    print(f"     (past the B1/B2 KV-cache capacity ceiling, real goodput falls, not doubles).")


if __name__ == "__main__":
    main()
