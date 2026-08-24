# A3 — Corrected cross-language analysis

**Command**: `python partA/corrected_analysis.py` (full output:
`partA/results/corrected_analysis_output.txt`, raw numbers:
`partA/results/a3_full_table.csv`)

**Setup**: A1's FLORES-200 devtest corpus (1012 parallel sentences x 6
languages), 3 tokenizers, 4 denominators, bugs 1-3 from A2 fixed
(`str.split()`, micro-averaging, no `.lower()`).

- **Tokenizers**: `gpt2` (tiktoken, the incumbent used by the original
  report), `google/muril-base-cased` (WordPiece, purpose-trained on Hindi +
  Dravidian + English — the required Indic-aware tokenizer),
  `facebook/nllb-200-distilled-600M` (SentencePiece, trained across all 200
  FLORES languages, including every language in this corpus).
- **Denominators**: whitespace word, UTF-8 byte, extended grapheme cluster
  (via `regex`'s `\X`), parallel sentence.

## Results — ratio to English, by tokenizer x denominator

**gpt2** (incumbent):

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| hin | 6.331 | 2.905 | 11.380 | 7.413 |
| kan | 18.480 | 4.781 | 19.838 | 13.585 |
| mal | 22.239 | 4.864 | 25.188 | 15.160 |
| tam | 20.284 | 4.868 | 20.560 | 15.537 |
| tel | 16.770 | 4.844 | 22.354 | 12.970 |

**MuRIL** (Indic-aware):

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| hin | 0.990 | 0.454 | 1.780 | 1.160 |
| kan | 1.450 | 0.375 | 1.557 | 1.066 |
| mal | 1.737 | 0.380 | 1.968 | 1.184 |
| tam | 1.383 | 0.332 | 1.401 | 1.059 |
| tel | 1.556 | 0.449 | 2.074 | 1.203 |

**NLLB-200-distilled-600M** (multilingual):

| lang | tok/word | tok/byte | tok/grapheme | tok/sentence |
|---|---|---|---|---|
| hin | 1.035 | 0.475 | 1.861 | 1.212 |
| kan | 1.854 | 0.480 | 1.990 | 1.363 |
| mal | 2.188 | 0.479 | 2.478 | 1.492 |
| tam | 1.849 | 0.444 | 1.874 | 1.416 |
| tel | 1.715 | 0.495 | 2.286 | 1.327 |

(Absolute per-language, per-tokenizer, per-denominator numbers are in
`a3_full_table.csv`; the tables above are ratios to that tokenizer's own
English row, since that's the quantity the report actually used.)

## Finding 1: the report's root-cause claim is wrong

REPORT_v0 states: *"Root cause: Hindi simply has more Unicode characters per
word, so any tokenizer will struggle. This is a property of the script, not
the tokenizer."*

That claim is falsified by this table. Under gpt2, hin/eng is 6.3x (word) to
11.4x (grapheme). Under MuRIL or NLLB — the same text, the same corpus, only
the tokenizer changed — hin/eng drops to 1.0-1.9x, and every Dravidian
language drops from double-digit multipliers (gpt2) to roughly 1.4-2.5x.
Swapping the tokenizer moves the multiplier by 3-10x. That is the signature
of a tokenizer-vocabulary problem (gpt2's BPE merges were learned almost
entirely on English/Latin-script text, so it falls back to inefficient
byte-level fragments on Indic scripts), not an inherent property of Hindi
or the Dravidian languages' scripts.

## Finding 2: which single number should drive the routing/cost decision

**Answer: tokens per UTF-8 byte of input, using whichever tokenizer is
actually deployed.**

Reasoning, working through the denominators:

- **tokens/word** and **tokens/grapheme** are contaminated by each
  language's own orthographic conventions (A2, flaw 4: Dravidian languages
  need only ~0.7x as many whitespace words as English to say the same
  thing; grapheme density varies with how much a script relies on combining
  marks). They don't hold anything about the *content* constant across
  languages — they hold a property of the *script* constant, which is the
  wrong thing for a cost decision.
- **tokens/parallel-sentence** is the theoretically cleanest: FLORES holds
  meaning constant by construction, so tokens/sentence directly answers "how
  many tokens does it cost to say the same thing in language X vs
  English?" But this denominator is a research-only luxury — production
  traffic isn't parallel-translated, so you can't compute "tokens per
  parallel sentence" on live requests. It's useful for calibration, not
  monitoring.
- **tokens/byte** is the practical answer: it's directly measurable on
  every live request (byte length of the input, no translation needed), and
  empirically it's the *most stable* denominator across languages for a
  fixed tokenizer — for NLLB, hin/kan/mal/tam/tel all sit in a tight
  0.44-0.50x-of-English band; for MuRIL, 0.33-0.45x. That stability means
  tok/byte reliably predicts relative serving cost per language without
  needing ground-truth parallel content, which is exactly the property you
  want in a metric that has to run on real, unparalleled traffic.

The hint in the assignment — "think hard about what the denominator is
supposed to hold constant across languages" — is the crux: tok/sentence
holds *meaning* constant (right for research validation), tok/byte holds
*something you can actually measure on live text* roughly constant per
script family (right for production). Word and grapheme counts hold neither
constant; they're artifacts of orthography.

## Finding 3: the two "independent confirmations" in the original report weren't independent

REPORT_v0's finding #2 says the tok/char number "agrees" with tok/word and
"confirms" it, concluding "no further measurement needed." Both numbers were
computed from the same `encode()` call on the same text with the same
`.lower()` preprocessing — they're two views of one measurement, not two
measurements. This table shows why that mattered: tok/word and tok/grapheme
(closest correlate to the original's tok/char) actually disagree with each
other by a wide margin per language (e.g. gpt2/mal: 22.2x word vs 25.2x
grapheme) — they're correlated but not interchangeable, and neither one
alone should have been treated as sufficient to skip further measurement.
