# A2 — Audit of `fertility.py` and the fertility metric

Six claims below: four code bugs, one conceptual flaw, one "looks
suspicious but is fine." Every claim ships with the exact command, the
before/after numbers, and one sentence on why the delta proves the claim.
Raw output for each experiment is in `partA/results/`.

## 1. Bug — phantom word from `line.split(" ")`

**Claim**: `words = line.split(" ")` (fertility.py:62) splits on a literal
single space, so any line with a doubled space produces an extra
empty-string "word," inflating the word-count denominator and deflating the
reported fertility on that line.

**Command**: `python partA/bugs/bug1_double_space.py`

**Before/after**:
| corpus | line | `split(" ")` words | `split()` words | fertility (bug) | fertility (fix) |
|---|---|---|---|---|---|
| eng_sample.txt:7 | "Please keep the books  in the cupboard." | 8 | 7 | 1.2500 | 1.4286 |
| hin_sample.txt:10 | "किताबें  अलमारी में रखी हैं।" | 6 | 5 | 7.5000 | 9.0000 |

At FLORES-200 scale (1012 lines/lang), the effect is real but small and
language-dependent: eng has 0 affected lines (Δ=0.0000), hin 6/1012
(Δ=−0.0018), but kan has 208/1012 affected lines (Δ=−0.4495, ~2% of its
22.57 base), tel 136 (Δ=−0.26), tam 75 (Δ=−0.13), mal 54 (Δ=−0.10).

**Why the delta proves the claim**: the fertility number changes by a
measurable, sign-consistent amount purely from switching `split(" ")` to
`split()` on the identical text and tokenization — the only variable that
changed is how whitespace is parsed, so the difference is attributable
entirely to that bug, and it always deflates (never inflates) the reported
number, matching the mechanism (extra denominator entry).

**Scope note**: this bug does not materially affect the eng/hin comparison
the original report made (hin: −0.02%), but would quietly bias any
comparison involving Kannada or Telugu on real traffic.

## 2. Bug — macro-average of per-line ratios instead of micro-average

**Claim**: `analyze()` (fertility.py:54-67) computes
`sum(per_line_fertility) / n` — the mean of per-line ratios — instead of
`total_tokens / total_words`. This gives every line equal weight regardless
of length, which is not the same quantity as "tokens per word across the
corpus."

**Command**: `python partA/bugs/bug2_macro_vs_micro.py`

**Before/after** (FLORES-200, all 6 languages, `split()`-fixed so this
isolates only the averaging method):

| lang | macro (script's method) | micro (total/total) | delta | delta % |
|---|---|---|---|---|
| eng | 1.2874 | 1.2782 | +0.0092 | +0.72% |
| hin | 7.8582 | 7.8179 | +0.0402 | +0.51% |
| kan | 23.0217 | 22.8216 | +0.2002 | +0.88% |
| mal | 27.6901 | 27.4619 | +0.2282 | +0.83% |
| tam | 25.2525 | 25.0492 | +0.2034 | +0.81% |
| tel | 20.8304 | 20.7145 | +0.1159 | +0.56% |

**Why the delta proves the claim**: holding tokenizer, corpus, and word-split
method fixed and changing only the averaging formula moves every language's
number in the same direction (macro > micro), by ~0.5-0.9% — consistent
with the mechanism (short lines get noisier per-line ratios and are
over-weighted). Real, but small — not enough on its own to explain the
report's ×5.89 headline.

## 3. Conceptual — `.lower()` before encoding is not neutral across scripts

**Claim**: `analyze()` lowercases every line before encoding (fertility.py:60),
commented "so casing doesn't add noise." Devanagari and the four Dravidian
scripts here have no case distinction, so this is a no-op for them — but
GPT-2's BPE vocabulary is case-sensitive, so lowercasing English text changes
which merges apply. The preprocessing step is not symmetric across the two
sides of the comparison it's meant to make fair.

**Command**: `python partA/bugs/bug3_lowercasing.py`

**Before/after** (FLORES-200, micro-averaged, `split()`-fixed):

| lang | fertility (lowercased) | fertility (as-is) | delta | delta % |
|---|---|---|---|---|
| eng | 1.2782 | 1.2348 | +0.0434 | **+3.51%** |
| hin | 7.8179 | 7.8176 | +0.0003 | +0.00% |
| kan | 22.8216 | 22.8202 | +0.0014 | +0.01% |
| mal | 27.4619 | 27.4612 | +0.0007 | +0.00% |
| tam | 25.0492 | 25.0478 | +0.0014 | +0.01% |
| tel | 20.7145 | 20.7086 | +0.0059 | +0.03% |

hin/eng ratio with lowercasing: **6.116x**. Without: **6.331x**.

**Why the delta proves the claim**: the five case-less scripts move by
≤0.03% (noise) while English alone moves 3.51% — an asymmetry that can only
come from `.lower()` interacting with GPT-2's case-sensitive vocabulary,
since nothing else differs between the two runs. Note the direction: contrary
to my first guess (see NOTEBOOK.md), lowercasing *shrinks* the reported
hin/eng multiplier by ~3.4%, it doesn't inflate it — the report's ×5.89 is
mildly conservative because of this bug, not exaggerated by it. Direction
matters and isn't guessable without measuring it.

## 4. Bug — `tok/char` denominator counts codepoints, not UTF-8 bytes

**Claim**: `chars = len(line)` (fertility.py:63) is a Python `str`, so
`len()` counts Unicode *codepoints*, not UTF-8 bytes. REPORT_v0's finding
#2 — *"the tok/char column agrees: 1.579 vs 0.226 = 7.0× worse per
character, which confirms the per-word number"* — is computed from exactly
this line. Devanagari codepoints (U+0900–U+097F) encode as 3 bytes each in
UTF-8; ASCII encodes 1:1. Dividing by codepoint count instead of byte count
therefore understates Hindi's actual byte footprint relative to English's,
inflating the reported tok/char ratio.

**Command**: `python partA/bugs/bug4_char_vs_byte.py`

**Before/after** (holding tokenizer, text, and `.lower()` identical to the
original script — only the `chars` denominator changes from `len(line)` to
`len(line.encode("utf-8"))`):

| corpus | lang | tok/char (`len()`, bug) | tok/byte (UTF-8, fix) | avg bytes/char |
|---|---|---|---|---|
| corpus_sample (REPORT_v0's exact files) | eng | 0.226 | 0.226 | 1.000 |
| corpus_sample (REPORT_v0's exact files) | hin | 1.579 | 0.599 | 2.634 |
| FLORES-200 (1012 lines/lang) | eng | 0.214 | 0.214 | 1.001 |
| FLORES-200 (1012 lines/lang) | hin | 1.529 | 0.595 | 2.572 |
| FLORES-200 (1012 lines/lang) | kan/mal/tam/tel | 2.64-2.74 | 0.98-1.00 | 2.67-2.76 |

hin/eng ratio on corpus_sample using `len()` (REPORT_v0's method):
**6.998x**, matching the report's "7.0x" to 3 significant figures — this
run reproduces REPORT_v0's exact numbers, confirming the isolation is
faithful to what the report actually computed. hin/eng ratio switching only
the denominator to UTF-8 bytes: **2.655x**. Same pattern holds at FLORES
scale: 7.144x (`len()`) vs 2.781x (bytes).

**Why the delta proves the claim**: holding tokenizer, text, and
preprocessing fixed and changing only how `chars` is counted moves the
hin/eng ratio from ~7.0x to ~2.7x — a >2.5x swing, entirely attributable to
codepoint-vs-byte counting, since `avg bytes/char` for English is ~1.0
(ASCII) but ~2.6-2.8 for Hindi and the four Dravidian languages
(multi-byte UTF-8). REPORT_v0's finding #2 treats this codepoint-based
number as an *independent confirmation* of the tok/word finding; it isn't
independent (same `encode()` call, same text) and the specific "7.0x"
figure it leans on is itself a denominator artifact, not a byte-accurate
measurement of relative cost. A3's tok/byte column (Finding 2) is the
corrected, byte-based number for production use — this experiment is what
directly proves REPORT_v0's original tok/char figure was miscounted, rather
than just asserting it.

## 5. Conceptual flaw (the "wrong thing to compute" one) — tokens/word as the denominator

**Claim**: the script computes exactly what "tokens per whitespace-split
word" says — but that's not a language-neutral unit. A "word" is an artifact
of each language's own orthographic and morphological conventions, not a
fixed quantity of meaning. Using it as the cross-language denominator
conflates two different things: tokenizer inefficiency, and how many
whitespace-delimited units a language happens to use to say the same thing.

**Command**: `python partA/bugs/flaw4_word_denominator.py`

**Evidence, part 1** — does word count stay constant across a parallel
(meaning-aligned) corpus? No:

| lang | avg words/sentence | relative to eng |
|---|---|---|
| eng | 21.64 | 1.00x |
| hin | 25.34 | 1.17x |
| kan | 15.91 | 0.74x |
| mal | 14.75 | 0.68x |
| tam | 16.58 | 0.77x |
| tel | 16.74 | 0.77x |

The four Dravidian languages need only 68-77% as many whitespace "words" as
English to express the *same content* (agglutinative morphology fuses case
markers and postpositions into the word); Hindi needs 17% more. This alone
proves "word" is not a stable unit to divide by.

**Evidence, part 2** — how much does the headline number move when the
denominator changes to something meaning-constant (tokens per parallel
sentence), same tokenizer, same corpus:

| metric | eng | hin | hin/eng ratio |
|---|---|---|---|
| tokens / word | 1.235 | 7.818 | 6.331 |
| tokens / parallel sentence | 26.72 | 198.09 | **7.413** |

**Why this proves the claim**: switching only the denominator — same
tokenizer, same text, same tokens — moves the headline ratio from 6.331x to
7.413x, a 17% swing. That swing is entirely attributable to what unit you
divide by, which is exactly the point: tokens/word doesn't hold anything
meaningful constant across languages, so its exact value (and by extension
the "×5.89" and "×5.89 ≈ ×7.0 so it's robust" argument in the report) is an
artifact of a somewhat arbitrary denominator choice, not a robust, corrected
fact about relative serving cost. **Important nuance**: the "corrected"
meaning-constant denominator here makes the Hindi/English gap look *worse*,
not better — so this flaw does not mean "the alarm was overblown." It means
the exact number quoted can't be trusted at face value, in either direction,
until you're deliberate about the denominator (see A3).

## 6. Looks suspicious but is fine — `random.seed(1337)`

**Claim**: `import random` / `random.seed(1337)  # reproducibility`
(fertility.py:21,25) looks like it should matter — a seed usually implies
something stochastic is happening — but `random` is never called anywhere
else in the file, so seeding it cannot affect any output.

**Command**: `python partA/bugs/nonbug_random_seed.py`

**Evidence**: (1) grep of the whole file: `random` appears on exactly 2
lines, the import and the seed call — zero other uses. (2) Ran the original
script against a byte-identical copy with the `random.seed(1337)` line
deleted, both on `--corpus eng=... --corpus hin=... --tokenizer gpt2`:
stdout was 244 characters in both cases and **byte-for-byte identical**.

**Why this proves the claim**: deleting the line and observing zero change
in output — not just reasoning "it's probably fine" — is direct evidence
of inertness. This is deliberately the "harmless thing" the assignment asks
us to distinguish from a real bug: it reads as suspicious (a fixed seed
signals "we made this reproducible," implying without it the numbers would
vary), but it's dead code sitting on top of a fully deterministic script.
Flagging it as a bug without this check would have cost points under the
evidence rule.

## Summary

| # | item | type | magnitude at FLORES scale |
|---|---|---|---|
| 1 | `split(" ")` phantom word | bug | ≤2% (language-dependent, 0 for eng) |
| 2 | macro- vs micro-average | bug | 0.5-0.9% |
| 3 | `.lower()` before encoding | bug (asymmetric) | 3.5% for eng, ~0% for Indic scripts |
| 4 | `tok/char` counts codepoints, not UTF-8 bytes | bug | ~7.0x → ~2.7x on hin/eng (>2.5x swing) |
| 5 | tokens/word denominator | **conceptual** | 17% swing in the headline ratio |
| 6 | `random.seed(1337)` | **not a bug** | 0% (proven inert) |

None of bugs 1-3, even combined, comes close to explaining the report's
×5.89 headline. Bug 4 alone, however, fully accounts for REPORT_v0's
"confirmed by two independent metrics" claim: its "7.0× worse per
character" figure is not an independent confirmation (tok/word and tok/char
are both derived from the same `encode()` call on the same text) *and* the
figure itself is inflated by counting codepoints instead of bytes — fixing
just the denominator drops it from 7.0x to 2.7x. The word-vs-byte-vs-
sentence denominator choice (#5) is where the remaining leverage is, which
is why A3 tests multiple denominators explicitly rather than patching bugs
1-4 and calling it corrected.
