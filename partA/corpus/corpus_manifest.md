# A1 — Eval corpus manifest

## Source

FLORES-200 (Facebook AI / Meta, "No Language Left Behind"), `devtest` split.
Sentence-level, professionally translated, parallel across 200 languages.
License: CC-BY-SA 4.0.

**Retrieval**: `partA/corpus/build_corpus.py` downloads the official public
release tarball (`https://dl.fbaipublicfiles.com/nllb/flores200_dataset.tar.gz`,
25,585,843 bytes, sha256 `b8b0b76783024b85797e5cc75064eb83fc5288b41e9654dabc7be6ae944011f6`)
and extracts the `devtest` file per language. See `NOTEBOOK.md` for why the
tarball was used instead of `datasets.load_dataset(...)`: both `facebook/flores`
and `openlanguagedata/flores_plus` on the HF Hub are gated, and the
`Muennighoff/flores200` mirror uses a legacy dataset-script format that
`datasets==5.0.1` refuses to execute. The tarball is the original, public,
unauthenticated source these all wrap.

Reproduce with:
```
cd partA/corpus
python build_corpus.py
```

## Languages and size

| lang | FLORES code | family | script | sentences |
|---|---|---|---|---|
| eng | eng_Latn | Indo-European (Germanic) | Latin | 1012 |
| hin | hin_Deva | Indo-European (Indo-Aryan) | Devanagari | 1012 |
| kan | kan_Knda | Dravidian | Kannada | 1012 |
| tam | tam_Taml | Dravidian | Tamil | 1012 |
| tel | tel_Telu | Dravidian | Telugu | 1012 |
| mal | mal_Mlym | Dravidian | Malayalam | 1012 |

Exceeds the assignment minimum (≥4 languages incl. English, Hindi, 2
Dravidian) — all four example Dravidian languages included rather than just
two, for a stronger cross-language comparison.

All six files are line-aligned: line *N* is the same sentence in every
language (verified programmatically in `build_corpus.py`'s final assertion,
and spot-checked manually — see `NOTEBOOK.md`).

## Domain

FLORES-200 sentences are drawn from Wikinews, Wikijunior, and WikiVoyage —
general-knowledge, encyclopedic/news register, translated by professional
human translators (not machine-translated, not crowd-sourced).

## Preprocessing

None beyond what `build_corpus.py` does: strip blank lines, UTF-8 decode.
Unicode normalization (NFC) is applied later, inside the tokenizer-audit
scripts themselves (matching what `fertility.py` does), not at corpus-build
time — kept separate so the corpus files are a faithful, unmodified copy of
the source release.

## What this corpus cannot tell you

This is a *register* benchmark, not a *product traffic* benchmark. FLORES is
news/encyclopedia-style text, professionally translated — it says nothing
about how our tokenizer performs on actual assistant conversations, which
skew shorter, more informal, and frequently code-mixed (e.g. Hindi/English
"Hinglish," common in real Indic-market chat traffic and entirely absent
here). Translated text also has known "translationese" statistical
properties (more literal, less idiomatic phrasing than native text), which
can shift tokenizer fertility in either direction relative to organic text.
1012 sentences per language is enough to estimate a stable mean fertility
(the numbers barely move between the `dev` and `devtest` splits in published
NLLB tokenizer studies) but is not large enough to characterize the tail —
rare scripts-mixing, code, numerals, emoji, or domain-specific vocab (product
names, slang) that a production router will actually see. Any cost model
built purely on this corpus should be treated as a first-order estimate,
re-validated against sampled live traffic before being used to size budgets
(see the production-monitoring metric in `A4_memo.md`).
