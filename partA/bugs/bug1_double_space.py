#!/usr/bin/env python3
"""
bug1_double_space.py -- isolate the effect of fertility.py's
`words = line.split(" ")` (literal single-space split) vs the fix,
`words = line.split()` (any whitespace run, no empty tokens).

A line with a doubled space produces an extra empty-string "word" under
split(" "), inflating the denominator and deflating the reported fertility
on that line. Both original sample corpora contain such a line:
  eng_sample.txt:7  "Please keep the books  in the cupboard."
  hin_sample.txt:10 "किताबें  अलमारी में रखी हैं।"

This script (a) shows the exact per-line word-count difference on the two
lines that actually trigger it, and (b) measures the aggregate effect on the
full FLORES-200 devtest corpus (1012 lines/language) built for A1.
"""

import glob
import os
import tiktoken

enc = tiktoken.get_encoding("gpt2")


def fertility_with_split(lines, split_fn):
    ratios = []
    for line in lines:
        line = line.lower()
        tokens = enc.encode(line)
        words = split_fn(line)
        ratios.append(len(tokens) / len(words))
    return sum(ratios) / len(ratios)


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def main():
    here = os.path.dirname(__file__)
    print("FORMULA: fertility = tokens / words")
    print('  bug (fertility.py):  words = line.split(" ")   -- literal single space')
    print("  fix:                 words = line.split()      -- any whitespace run")
    print()
    print("=" * 70)
    print("PART 1: exact lines that trigger the bug (original sample corpus)")
    print("=" * 70)
    for name, path in [
        ("eng", os.path.join(here, "..", "original", "corpus_sample", "eng_sample.txt")),
        ("hin", os.path.join(here, "..", "original", "corpus_sample", "hin_sample.txt")),
    ]:
        for line in read_lines(path):
            w_bug = line.split(" ")
            w_fix = line.split()
            if len(w_bug) != len(w_fix):
                tokens = enc.encode(line.lower())
                print(f"\n[{name}] line: {line!r}")
                print(f"  split(\" \") -> {len(w_bug)} words {w_bug!r}")
                print(f"  split()    -> {len(w_fix)} words {w_fix!r}")
                print(f"  tokens={len(tokens)}  fertility(bug)={len(tokens)/len(w_bug):.4f}"
                      f"  fertility(fix)={len(tokens)/len(w_fix):.4f}"
                      f"  delta={len(tokens)/len(w_bug) - len(tokens)/len(w_fix):+.4f}")

    print()
    print("=" * 70)
    print("PART 2: aggregate effect on FLORES-200 devtest corpus (A1, 1012 lines/lang)")
    print("=" * 70)
    corpus_dir = os.path.join(here, "..", "corpus", "flores200")
    files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
    if not files:
        print("(FLORES corpus not found -- run partA/corpus/build_corpus.py first)")
        return

    col_bug = 'fert split(" ")'
    col_fix = "fert split()"
    print(f"{'lang':<6}{'lines w/ multi-space':>22}{col_bug:>18}{col_fix:>16}{'delta':>10}")
    for path in files:
        lang = os.path.splitext(os.path.basename(path))[0]
        lines = read_lines(path)
        n_affected = sum(1 for ln in lines if "  " in ln)
        f_bug = fertility_with_split(lines, lambda s: s.split(" "))
        f_fix = fertility_with_split(lines, lambda s: s.split())
        print(f"{lang:<6}{n_affected:>22}{f_bug:>18.4f}{f_fix:>16.4f}{f_bug - f_fix:>+10.4f}")


if __name__ == "__main__":
    main()
