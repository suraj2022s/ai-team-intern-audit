# B4 — Confirming the B2 mechanism

The single counter I'd pull is the serving engine's **scheduler preemption
counter** — in the CSV we already have it as `preempted_seqs`, and in a live
vLLM-style stack it's the equivalent Prometheus counter
(`vllm:num_preemptions_total`), ideally paired with `vllm:gpu_cache_usage_perc`
(the live version of `kv_cache_util`). If the B2 mechanism (KV-cache
exhaustion forcing eviction-and-recompute, not compute saturation) is
correct, I'd expect `num_preemptions_total` to sit at essentially zero for
all concurrency levels up to ~24-25 sequences at this prompt length, then
step-change sharply upward right at the batch 24→32 transition — matching
the CSV's own jump from 0 to 7 preempted sequences — and continue climbing
with concurrency (23 at batch 48). I'd also expect `gpu_cache_usage_perc` to
plateau at its ceiling (~0.97, matching `kv_cache_util`) starting at exactly
the same point rather than continuing to rise with batch size, since once
the cache is full it can't be "more full" — new admissions instead show up
as preemptions of existing sequences. Seeing the preemption counter's onset
line up with the kv-cache-utilization plateau, both at the same batch size
predicted analytically in B1 (~25 sequences), is the confirmation that ties
the arithmetic (B1) to the observed anomaly (B2) to the corrected throughput
number (B3) as one consistent story rather than three separate observations.
