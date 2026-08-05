# A4 — Recommendation memo: tokenizer routing & cost

**To**: Leadership (routing/capacity decision)
**Re**: Audit of `REPORT_v0.md` §1 (tokenizer fertility)
**Bottom line**: the underlying alarm (Indic-language serving costs more)
is directionally real, but the report's specific numbers and root cause are
wrong. The 6x figure is a property of *which tokenizer we're using*, not of
Hindi or the Dravidian languages. Fix the tokenizer before budgeting for it.

## Corrected headline numbers

Evaluated on FLORES-200 (1012 parallel sentences, eng + hin + kan/mal/tam/tel),
3 tokenizers x 4 denominators — full detail in `A3_corrected_analysis.md`.

| tokenizer | hin/eng | Dravidian/eng (range) | basis |
|---|---|---|---|
| gpt2 (current) | 6.3x (word) / 2.9x (byte) | 4.8x-4.9x (byte) | incumbent, English-centric BPE |
| MuRIL (Indic-aware) | 1.0x (word) / 0.45x (byte) | 0.33-0.45x (byte) | trained on Indic scripts |
| NLLB-200 (multilingual) | 1.0x (word) / 0.48x (byte) | 0.44-0.50x (byte) | trained on Indic scripts |

Recommended headline metric: **tokens per UTF-8 byte**, because it's
measurable on live traffic (no parallel/translated ground truth needed) and
empirically the most stable denominator across languages once you've fixed a
tokenizer (see A3, Finding 2). Under that metric, the true multiplier for an
Indic-aware tokenizer is **~2-3x**, not 6x — and note tok/byte is *less than
1.0* for every language here, meaning Indic-script text is actually more
token-efficient per byte with an Indic-aware tokenizer than English is, once
you're not fighting the tokenizer's vocabulary.

## Routing recommendation

Do not route Indic traffic to a separate model purely to "absorb" a 6x cost
multiplier — that multiplier is mostly an artifact of serving Indic text
through an English-optimized tokenizer (gpt2). The higher-leverage fix is
**switching the tokenizer** (or routing to a model that already uses an
Indic-aware one, e.g. MuRIL/NLLB-family vocab) before making capacity
decisions. Once that's done, budget roughly **2-3x** per-request cost for
Hindi and the Dravidian languages relative to English (tok/byte basis), not
6x. If a separate Indic-specialized serving path is still desired for other
reasons (latency isolation, model quality), size its capacity against the
2-3x figure, not the original 6x.

## Biggest caveat

FLORES-200 is professionally translated news/encyclopedia text — it is not
representative of actual assistant chat traffic, which is shorter, more
informal, and frequently code-mixed (Hindi/English "Hinglish" is common in
real Indic-market usage and has zero representation here). Translated text
also carries "translationese" artifacts that can shift fertility in either
direction versus organic text. This benchmark should be read as "the
relative-cost picture changes dramatically with tokenizer choice," not as
"the exact 2-3x multiplier is what you'll see in production." (See
`corpus/corpus_manifest.md` for the full caveat.)

## Metric to monitor in production

**Live tokens-per-byte-of-input, sliced by language, tracked against the
FLORES-benchmarked ratio for the deployed tokenizer.** If live tok/byte for
a language drifts meaningfully from its FLORES baseline (e.g. real traffic
skews toward code-mixed or emoji-heavy text that behaves differently than
clean translated prose), that's the signal this offline analysis has gone
stale and needs re-validation — ideally cross-checked periodically against
a small held-out set of real (not synthetic/translated) requests per
language, since tok/byte's stability was only demonstrated on FLORES here.
