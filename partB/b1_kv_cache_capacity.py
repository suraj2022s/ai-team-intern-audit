#!/usr/bin/env python3
"""
b1_kv_cache_capacity.py -- B1: from bench/model_spec.md alone, compute
(a) KV-cache bytes per token, exactly, and (b) the approximate max number
of concurrent 4096-token sequences the GPU can hold. Then check the
prediction against bench/bench_log.csv.

All arithmetic is executed here (not by hand) so it can be re-run/modified
live in the defense.
"""

import csv
import os

# ---- from bench/model_spec.md ----
LAYERS = 28
KV_HEADS = 8          # GQA: 8 KV heads (vs 24 Q heads -- irrelevant to KV size)
HEAD_DIM = 128
BYTES_PER_PARAM_FP16 = 2
PARAMS = 4.2e9
GPU_MEM_GB = 24
GPU_MEM_UTIL = 0.92
NON_KV_OVERHEAD_GB = 1.6
MAX_MODEL_LEN = 4096

# Unit convention: model_spec.md gives GPU memory in "GB". We treat this as
# GB = 1e9 bytes (decimal), matching how NVIDIA/vendors quote card memory
# (a 24GB L4 card has 24e9 bytes, not 24*1024^3). This assumption is stated
# explicitly because it changes the answer by ~7% vs GiB -- exactly the kind
# of thing a defense counterfactual would probe.
GB = 1e9


def kv_bytes_per_token():
    # K and V caches, each: layers x kv_heads x head_dim x bytes/param
    per_kv = LAYERS * KV_HEADS * HEAD_DIM * BYTES_PER_PARAM_FP16
    return 2 * per_kv  # x2 for K and V


def max_concurrent_sequences():
    kv_bpt = kv_bytes_per_token()
    total_mem = GPU_MEM_GB * GB * GPU_MEM_UTIL
    weights_mem = PARAMS * BYTES_PER_PARAM_FP16
    overhead_mem = NON_KV_OVERHEAD_GB * GB
    usable_kv_mem = total_mem - weights_mem - overhead_mem
    max_seqs = usable_kv_mem / (kv_bpt * MAX_MODEL_LEN)
    return kv_bpt, total_mem, weights_mem, overhead_mem, usable_kv_mem, max_seqs


def main():
    kv_bpt, total_mem, weights_mem, overhead_mem, usable_kv_mem, max_seqs = max_concurrent_sequences()

    print("(a) KV-cache bytes per token")
    print(f"    = 2 (K,V) x layers({LAYERS}) x kv_heads({KV_HEADS}) x head_dim({HEAD_DIM}) x bytes/param({BYTES_PER_PARAM_FP16})")
    print(f"    = 2 x {LAYERS} x {KV_HEADS} x {HEAD_DIM} x {BYTES_PER_PARAM_FP16}")
    print(f"    = {kv_bpt:,} bytes/token  (~{kv_bpt/1024:.1f} KiB/token)")

    print("\n(b) Max concurrent 4096-token sequences")
    print(f"    total GPU memory budget   = {GPU_MEM_GB} GB x {GPU_MEM_UTIL} util = {total_mem/GB:.3f} GB")
    print(f"    - model weights           = {PARAMS:.2e} params x {BYTES_PER_PARAM_FP16} bytes = {weights_mem/GB:.3f} GB")
    print(f"      (NOT called out separately in model_spec.md's overhead line, but weights")
    print(f"       obviously occupy GPU memory too -- omitting this would overstate capacity)")
    print(f"    - non-KV runtime overhead = {overhead_mem/GB:.3f} GB")
    print(f"    = usable KV-cache memory  = {usable_kv_mem/GB:.3f} GB")
    print(f"    max_seqs = usable_KV_mem / (bytes/token x {MAX_MODEL_LEN})")
    print(f"             = {usable_kv_mem/GB:.3f}e9 / ({kv_bpt} x {MAX_MODEL_LEN})")
    print(f"             = {max_seqs:.2f}  -> ~{int(max_seqs)} concurrent full-length (4096-token) sequences")

    print("\n(c) Check against bench_log.csv")
    here = os.path.dirname(__file__)
    log_path = os.path.join(here, "bench", "bench_log.csv")
    with open(log_path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    print(f"    {'batch':>6}{'prompt_len':>12}{'gen_len':>9}{'total_ctx':>10}{'preempted_seqs':>16}{'kv_cache_util':>15}")
    for r in rows:
        total_ctx = int(r["prompt_len"]) + int(r["gen_len"])
        print(f"    {r['batch_size']:>6}{r['prompt_len']:>12}{r['gen_len']:>9}{total_ctx:>10}"
              f"{r['preempted_seqs']:>16}{r['kv_cache_util']:>15}")

    print("\n(b-naive) What if you forgot to subtract model weights?")
    naive_usable_kv_mem = total_mem - overhead_mem
    naive_max_seqs = naive_usable_kv_mem / (kv_bpt * MAX_MODEL_LEN)
    overstatement_pct = (naive_max_seqs - max_seqs) / max_seqs * 100
    print(f"    naive usable KV memory = {total_mem/GB:.3f} - {overhead_mem/GB:.3f} (overhead only) = {naive_usable_kv_mem/GB:.3f} GB")
    print(f"    naive max_seqs = {naive_usable_kv_mem/GB:.3f}e9 / ({kv_bpt} x {MAX_MODEL_LEN}) = {naive_max_seqs:.2f} -> ~{int(naive_max_seqs)} sequences")
    print(f"    overstatement vs the correct {max_seqs:.2f}: +{overstatement_pct:.1f}%")

    print("\n(b-fp8) What if the KV cache itself were fp8 instead of fp16?")
    fp8_kv_bpt = kv_bpt // 2  # 1 byte/param instead of 2 -- weights untouched, only the KV cache quantizes
    fp8_max_seqs = usable_kv_mem / (fp8_kv_bpt * MAX_MODEL_LEN)
    print(f"    fp8 KV bytes/token = {kv_bpt} / 2 = {fp8_kv_bpt:,}")
    print(f"    fp8 max_seqs = {usable_kv_mem/GB:.3f}e9 / ({fp8_kv_bpt} x {MAX_MODEL_LEN}) = {fp8_max_seqs:.2f} -> ~{int(fp8_max_seqs)} sequences")
    print(f"    ratio vs fp16 ceiling ({max_seqs:.2f}): {fp8_max_seqs/max_seqs:.2f}x")

    print(f"\n    Predicted ceiling: ~{int(max_seqs)} concurrent 4096-token sequences.")
    print(f"    In the log, rows with prompt_len=3584 + gen_len=512 = 4096 total context:")
    print(f"      batch=24: preempted_seqs=0, kv_cache_util=0.93  (fits cleanly)")
    print(f"      batch=32: preempted_seqs=7, kv_cache_util=0.97  (scheduler starts preempting)")
    print(f"    -> the predicted ceiling ({int(max_seqs)}) should fall between 24 and 32 if the")
    print(f"       arithmetic is right. {'MATCH' if 24 <= max_seqs <= 32 else 'MISMATCH -- check assumptions'}")

    print("\n(d) Tighter check: predict kv_cache_util directly for the batch=24 row")
    batch24_kv_bytes = 24 * MAX_MODEL_LEN * kv_bpt
    predicted_util = batch24_kv_bytes / usable_kv_mem
    print(f"    24 sequences x {MAX_MODEL_LEN} tokens x {kv_bpt} bytes/token = {batch24_kv_bytes/GB:.3f} GB used")
    print(f"    predicted kv_cache_util = {batch24_kv_bytes/GB:.3f} / {usable_kv_mem/GB:.3f} = {predicted_util:.3f}")
    print(f"    logged kv_cache_util at batch=24, prompt=3584            = 0.93")
    print(f"    -> predicted {predicted_util:.2f} vs logged 0.93: "
          f"{'MATCH (independently confirms both the bytes/token formula AND the usable-memory accounting)' if abs(predicted_util-0.93) < 0.01 else 'off -- recheck assumptions'}")


if __name__ == "__main__":
    main()
