# B3 — The misread column and the honest goodput

**Command**: `python partB/b3_goodput.py` (full output: `b3_output.txt`)

## What's the misread column?

`reported_tok_s` is not decode (generation) throughput. It's
`num_requests x (prompt_len + gen_len) / wall_clock_s` — i.e. it counts the
**one-shot prefill tokens** (the entire prompt, processed in a single
forward pass) as if they were part of the streamed generation rate.

Verified on the batch=24, prompt=3584 row: `24 x (3584+512) / 61.16 =
1607.3`, matching the logged `reported_tok_s = 1607.4` to within rounding.

This single misread explains both of REPORT_v0 §2's conclusions:

1. **"Longer prompts give better throughput"** — a longer prompt puts more
   tokens into the one-time prefill count in the numerator, without
   changing how fast tokens are actually generated per second. It looks
   like better GPU utilization; it's really just a bigger one-off addend.
2. **"Batch 48 will deliver ~3200 tok/s"** — extrapolated by doubling the
   batch-24 *reported* rate. Doubling the wrong metric doesn't fix that it's
   the wrong metric, and (per B2) batch 48 is also well past the KV-cache
   capacity ceiling where the trend reverses anyway. Logged `reported_tok_s`
   at batch=48 is actually **1298.5** — lower than batch 24, not ~3200.

## Honest goodput of the batch-24, prompt-3584 row — two independent ways

**Way 1 — tokens actually generated, over wall clock:**
```
num_requests x gen_len / wall_clock_s = 24 x 512 / 61.16 = 200.9 tok/s
```

**Way 2 — from the per-token decode latency (independent measurement):**
```
batch_size x (1000 / itl_ms_p50) = 24 x (1000 / 96.07) = 249.8 tok/s
```

Both land in the same ballpark (200-250 tok/s), roughly **6-8x below** the
reported 1607.4 tok/s. Two derivations from two different columns
(`wall_clock_s`+`gen_len` vs. `itl_ms_p50`) agreeing on the same order of
magnitude is what makes this a credible correction, not just a guess.

## What the report should have said

*"`reported_tok_s` includes one-time prefill tokens, not just generated
tokens — it is not a decode-throughput metric and should not be used to
compare prompt lengths or extrapolate batch scaling. The honest generation
throughput at batch=24/prompt=3584 is ~200-250 tok/s, not 1607 tok/s.
Longer prompts do not improve GPU utilization; they inflate this specific
counter. Batch 48 does not deliver ~3200 tok/s — logged throughput at
batch 48 is lower than at batch 24 in every metric, because batch 48 sits
past the KV-cache capacity ceiling (see B1/B2), where the scheduler starts
preempting sequences instead of serving more of them."*

## A bonus signal that corroborates B2

Repeating way 2's calculation at batch=48 gives **480.0 tok/s** — *higher*
than batch 24's 249.8, even though way 1 correctly shows batch 48 goodput
falling (162.3 tok/s). That's because way 2 (`batch x 1000/itl_ms_p50`)
implicitly assumes every sequence in the batch is decoding productively
every step; once the scheduler starts preempting 23 of 48 sequences, that
assumption breaks — preempted sequences occupy a "batch slot" without
contributing steady decode progress, so multiplying the full batch size by
the emitted-token latency overstates real throughput. Way 1, which counts
total real output over total real elapsed time, has no such blind spot. The
fact that the two methods **agree at batch=24 (no preemption)** and
**diverge sharply at batch=48 (heavy preemption)** is itself independent
evidence for the preemption mechanism described in B2.
