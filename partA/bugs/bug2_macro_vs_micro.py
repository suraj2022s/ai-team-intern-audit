#!/usr/bin/env python3
"""
bug2_macro_vs_micro.py -- isolate the effect of averaging *per-line ratios*
(fertility.py's `sum(per_line_fertility) / n`, a macro-average that weights
every line equally regardless of length) vs. the micro-average
(`total_tokens / total_words`, which weights every word equally).

Uses `line.split()` (not `split(" ")`) for word-counting in both cases, so
this experiment isolates ONLY the averaging-method effect and doesn't
conflate it with bug 1.

Checked on both corpora: the original 10-line corpus_sample (Part 1) and
the full FLORES-200 devtest corpus (Part 2). Macro-vs-micro is a
statistical property of line-length variance across many lines, so a
10-line sample is expected to be too small/noisy to show a reliable
delta -- Part 1 exists to demonstrate that directly, not just assert it.
"""

import glob
import os
import tiktoken

enc = tiktoken.get_encoding("gpt2")


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def macro_and_micro(lines):
    per_line_ratios = []
    total_tokens = 0
    total_words = 0
    for line in lines:
        line = line.lower()
        tokens = enc.encode(line)
        words = line.split()
        per_line_ratios.append(len(tokens) / len(words))
        total_tokens += len(tokens)
        total_words += len(words)
    macro = sum(per_line_ratios) / len(per_line_ratios)
    micro = total_tokens / total_words
    return macro, micro


def report(files_by_lang):
    print(f"{'lang':<6}{'macro (per-line mean)':>24}{'micro (total/total)':>22}{'delta':>10}{'delta %':>10}")
    for lang, path in files_by_lang.items():
        lines = read_lines(path)
        macro, micro = macro_and_micro(lines)
        delta = macro - micro
        pct = 100 * delta / micro
        print(f"{lang:<6}{macro:>24.4f}{micro:>22.4f}{delta:>+10.4f}{pct:>+9.2f}%")


def main():
    here = os.path.dirname(__file__)

    print("=" * 70)
    print("PART 1: original corpus_sample (10 lines/lang, eng+hin only)")
    print("=" * 70)
    sample_files = {
        "eng": os.path.join(here, "..", "original", "corpus_sample", "eng_sample.txt"),
        "hin": os.path.join(here, "..", "original", "corpus_sample", "hin_sample.txt"),
    }
    report(sample_files)

    print()
    print("=" * 70)
    print("PART 2: FLORES-200 devtest corpus (A1, 1012 lines/lang)")
    print("=" * 70)
    corpus_dir = os.path.join(here, "..", "corpus", "flores200")
    files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
    if not files:
        print("(FLORES corpus not found -- run partA/corpus/build_corpus.py first)")
        return
    flores_files = {os.path.splitext(os.path.basename(p))[0]: p for p in files}
    report(flores_files)


if __name__ == "__main__":
    main()
