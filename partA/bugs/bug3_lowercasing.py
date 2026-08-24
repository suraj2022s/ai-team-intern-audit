#!/usr/bin/env python3
"""
bug3_lowercasing.py -- isolate the effect of fertility.py's `line.lower()`
before encoding.

Devanagari, Kannada, Tamil, Telugu, and Malayalam have no case distinction,
so lowercasing is a semantic no-op for them. GPT-2's BPE vocabulary is
case-sensitive (learned separate merges for "The"/"the" etc.), so lowercasing
English text before encoding is NOT a no-op there -- it changes which BPE
merges apply. The intern's comment says lowercasing is "so casing doesn't
add noise to the comparison" -- this experiment checks whether that's true,
or whether it instead asymmetrically favors one side of the comparison.

Uses `line.split()` and micro-averaging (bugs 1 & 2 fixed) so this isolates
ONLY the lowercasing effect.

Checked on both corpora: the original 10-line corpus_sample (Part 1) and
the full FLORES-200 devtest corpus (Part 2), same reasoning as bug 2 --
a BPE-merge effect like this is a statistical property that a 10-line
sample may not show reliably, so Part 1 exists to check that directly.
"""

import glob
import os
import tiktoken

enc = tiktoken.get_encoding("gpt2")


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def micro_fertility(lines, do_lower):
    total_tokens = 0
    total_words = 0
    for line in lines:
        text = line.lower() if do_lower else line
        tokens = enc.encode(text)
        words = text.split()
        total_tokens += len(tokens)
        total_words += len(words)
    return total_tokens / total_words


def report(files_by_lang):
    print(f"{'lang':<6}{'fert (lowercased)':>20}{'fert (as-is)':>16}{'delta':>10}{'delta %':>10}")
    results = {}
    for lang, path in files_by_lang.items():
        lines = read_lines(path)
        f_lower = micro_fertility(lines, True)
        f_raw = micro_fertility(lines, False)
        results[lang] = (f_lower, f_raw)
        delta = f_lower - f_raw
        pct = 100 * delta / f_raw
        print(f"{lang:<6}{f_lower:>20.4f}{f_raw:>16.4f}{delta:>+10.4f}{pct:>+9.2f}%")

    if "eng" in results and "hin" in results:
        print()
        eng_lower, eng_raw = results["eng"]
        hin_lower, hin_raw = results["hin"]
        ratio_lower = hin_lower / eng_lower
        ratio_raw = hin_raw / eng_raw
        print(f"hin/eng fertility ratio WITH lowercasing:    {ratio_lower:.3f}x")
        print(f"hin/eng fertility ratio WITHOUT lowercasing: {ratio_raw:.3f}x")
        print(f"How much of the reported multiplier is attributable to lowercasing: "
              f"{ratio_lower - ratio_raw:+.3f}x ({100*(ratio_lower-ratio_raw)/ratio_raw:+.2f}%)")
    return results


def main():
    here = os.path.dirname(__file__)
    print("FORMULA: fertility = tokens / words  (micro-averaged, split()-fixed)")
    print("  computed on line.lower() vs. line as-is -- only the .lower() step changes")
    print()
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
