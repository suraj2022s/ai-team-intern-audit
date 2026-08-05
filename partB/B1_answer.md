# B1 — KV-cache capacity

**Command**: `python partB/b1_kv_cache_capacity.py` (full output: `b1_output.txt`)

## (a) KV-cache bytes per token, exactly

```
2 (K and V) x layers(28) x kv_heads(8, GQA) x head_dim(128) x bytes/param(fp16=2)
= 2 x 28 x 8 x 128 x 2
= 114,688 bytes/token  (~112.0 KiB/token)
```

Uses `kv_heads=8` (the GQA count), not the 24 query heads — the KV cache
stores one K/V pair per KV head per layer per token, independent of how
many query heads share each KV head.

## (b) Max concurrent 4096-token sequences

```
usable GPU memory  = 24 GB x 0.92 (gpu_memory_utilization)        = 22.080 GB
- model weights    = 4.2e9 params x 2 bytes (fp16)                =  8.400 GB
- non-KV overhead  = (given in model_spec.md)                     =  1.600 GB
= usable KV memory                                                = 12.080 GB

max concurrent 4096-token sequences = 12.080e9 / (114,688 bytes/token x 4096 tokens)
                                     = 25.72  ->  ~25 sequences
```

**Note on model weights**: `model_spec.md`'s "non-KV runtime overhead" line
(1.6 GB, "activations, CUDA graphs, etc.") does not mention the model
weights themselves — but weights obviously sit in GPU memory too (8.4 GB
for a 4.2B-param fp16 model, larger than the overhead line and larger than
the entire non-weight budget). Omitting them would have overstated capacity
by ~230% (would predict ~59 sequences instead of ~25). Including them is
the correct reading of "how much memory is actually left for KV cache."

**Unit convention**: GB = 1e9 bytes throughout (decimal, matching how GPU
vendors quote card memory), not GiB = 1024³ bytes. Using GiB instead would
shift usable KV memory to ~11.25 GB and the ceiling to ~24 sequences — still
consistent with the log, but worth being explicit about since this is
exactly the kind of assumption a defense counterfactual would probe.

## Check against the log

Two independent checks, both against `bench_log.csv` rows at `prompt_len=3584,
gen_len=512` (total context 4096, matching the question's "4096-token
sequences"):

1. **Bracket check**: predicted ceiling (25.72) falls exactly between
   batch=24 (0 preemptions, `kv_cache_util=0.93`, fits cleanly) and batch=32
   (7 preemptions, `kv_cache_util=0.97`, scheduler starts evicting). That's
   where a ~25-sequence hard ceiling should show up in the data — and it
   does.
2. **Tighter check**: predicted `kv_cache_util` at batch=24 directly —
   `24 x 4096 x 114,688 bytes / 12.080e9 bytes usable = 0.933`. Logged value:
   `0.93`. This independently confirms both the bytes/token formula and the
   usable-memory accounting (weights + overhead subtraction) in one shot,
   not just the rough ceiling location.
