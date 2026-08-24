# B2 — Throughput anomaly in the long-context sweep

## The anomaly

Naive expectation: throughput scales with batch size (more concurrent
requests = more total tokens/sec, at least until compute-bound). The
`prompt_len=3584` rows of `bench_log.csv` violate this past batch=24:

| batch | wall_clock_s | reported_tok_s | preempted_seqs | kv_cache_util | e2e_ms_p95 |
|---|---|---|---|---|---|
| 4 | 28.98 | 565.4 | 0 | 0.16 | 32,673 |
| 8 | 36.30 | 902.6 | 0 | 0.31 | 39,983 |
| 16 | 49.97 | 1311.4 | 0 | 0.62 | 54,602 |
| **24** | 61.16 | **1607.4** (peak) | 0 | 0.93 | 69,221 |
| 32 | 94.71 | 1384.0 | **7** | 0.97 | 97,466 |
| 48 | 151.41 | 1298.5 | **23** | 0.97 | 105,428 |

Throughput rises monotonically through batch 24, then **falls** as batch
grows further (1607.4 → 1384.0 → 1298.5), even though more requests are
being submitted each time. That's the anomaly: doubling the batch from 24
to 48 makes throughput *worse*, not better.

## Mechanism

This is exactly where B1's predicted capacity ceiling (~25.7 concurrent
4096-token sequences) sits. Batch 24 (0.93 `kv_cache_util`, matching B1's
predicted 0.933 almost exactly) is the last row that fits in KV-cache memory
without eviction. Batch 32 and 48 exceed that ceiling: `preempted_seqs`
jumps from 0 to 7 to 23, and `kv_cache_util` pins at 0.97 (essentially
maxed — it can't go higher, so the "extra" batch slots have nowhere to put
their KV cache). When a sequence is preempted, the serving engine evicts its
KV cache to admit others, then must **recompute that sequence's prefill
from scratch** when it's rescheduled — burning GPU cycles on repeated work
instead of new output. `e2e_ms_p95` balloons in lockstep (69.2s → 97.5s →
105.4s), which is the direct symptom of requests stalling behind
re-admission, not evidence of heavier but still-productive compute. In
short: **past ~24-25 concurrent long-context sequences, we're not
compute-bound, we're KV-cache-memory-bound, and the scheduler starts
thrashing** — evicting and re-prefilling sequences rather than making net
progress. B3 independently supports this: honest decode goodput (not the
inflated `reported_tok_s`) is 200.9 tok/s at batch 24 vs. only 162.3 tok/s
at batch 48 — real throughput drops even more than the (already-wrong)
`reported_tok_s` column suggests, and the two independent goodput formulas
in B3 diverge sharply exactly at the preemption-heavy rows, which is itself
a signature of the thrashing.

## Proposed change and predicted effect

**Cap admission (`max_num_seqs` or equivalent scheduler concurrency limit)
at 24 for prompt_len≈3584-token workloads**, matching B1's measured/predicted
capacity ceiling, instead of letting the scheduler accept up to 48
concurrent requests and preempt its way through the overflow.

**Predicted quantitative effect**, using the log's own batch-24 numbers as
the target state we'd recover: instead of batch-48's real goodput of 162.3
tok/s (B3, way 1) and 105.4s p95 latency, capping at 24 concurrent requests
per instance (with any excess queued, not preempted) would put per-instance
throughput back at batch-24's ~200.9 tok/s honest goodput — a **~24%
recovery** in real generation throughput — while cutting p95 latency from
105.4s to 69.2s (a **~34% reduction**), and eliminating the 23 recompute
events (and the wasted compute they represent) entirely. This trades total
concurrency for per-request latency/throughput quality — traffic above the
cap queues instead of thrashing, which is a better failure mode for a
capacity-planning conversation than "accept everything and let the
scheduler silently degrade."

(A second-order option worth flagging for capacity growth rather than just
avoiding the cliff: fp8 KV-cache quantization would halve bytes/token
(B1's 114,688 B/token → 57,344 B/token), which by the same B1 formula
raises the concurrent-sequence ceiling to **~51 (exactly 2.00x)** — i.e.
raise the cliff instead of just staying under it. This is now the `(b-fp8)`
block in `partB/b1_kv_cache_capacity.py` / `b1_output.txt`, computed by the
script rather than asserted here, after an earlier pass found a different
hand-typed B1 number (the weights-omitted scenario) that turned out to be
wrong — same fix applied preemptively to this one. That's a larger change
with its own accuracy tradeoffs (fp8 KV cache trades off numerical
precision, not just memory), so the admission-cap fix is still the one I'd
recommend first — this is flagged as the next lever, not a replacement.)
