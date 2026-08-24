#!/usr/bin/env python3
"""
flaw4_word_denominator.py -- the conceptual flaw. fertility.py computes
exactly what it says (tokens per whitespace-delimited word), but that's the
wrong quantity for a cross-language cost comparison, because "word" is not
a unit held constant across languages -- it's an artifact of each
language's own orthographic convention for where to put spaces.

FLORES-200 is sentence-aligned: line N in every language file expresses the
same content. That lets us hold MEANING constant and check whether "word
count" is actually constant too. If it isn't, then tokens/word is
conflating two different things: (1) how efficient the tokenizer is, and
(2) how many whitespace-delimited units this language's orthography happens
to use to say the same thing. This script measures both denominators and
shows how much the headline hin/eng multiplier moves when you swap one for
the other.
"""

import glob
import os
import tiktoken

enc = tiktoken.get_encoding("gpt2")


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def main():
    here = os.path.dirname(__file__)
    corpus_dir = os.path.join(here, "..", "corpus", "flores200")
    files = sorted(glob.glob(os.path.join(corpus_dir, "*.txt")))
    if not files:
        print("(FLORES corpus not found -- run partA/corpus/build_corpus.py first)")
        return

    print("FORMULA:")
    print("  tokens/word     = total_tokens / total_words")
    print("  tokens/sentence = total_tokens / num_parallel_sentences")
    print()
    print("Step 1: does whitespace word-count stay constant across a parallel corpus")
    print("(same meaning, same sentence, different language)?\n")
    print(f"{'lang':<6}{'sentences':>10}{'total words':>13}{'avg words/sent':>16}")
    words_per_sent = {}
    tokens_total = {}
    for path in files:
        lang = os.path.splitext(os.path.basename(path))[0]
        lines = read_lines(path)
        total_words = sum(len(ln.split()) for ln in lines)
        total_tokens = sum(len(enc.encode(ln)) for ln in lines)
        words_per_sent[lang] = total_words / len(lines)
        tokens_total[lang] = total_tokens
        print(f"{lang:<6}{len(lines):>10}{total_words:>13}{words_per_sent[lang]:>16.2f}")

    base = words_per_sent["eng"]
    print(f"\nwords/sentence relative to eng (should be ~1.0x if 'word' were a")
    print(f"language-neutral unit of meaning -- it is not):")
    for lang, wps in words_per_sent.items():
        print(f"  {lang}: {wps/base:.2f}x eng's words/sentence")

    print()
    print("Step 2: headline hin/eng multiplier under three denominators")
    print("(all use the SAME tokenizer, gpt2, and the SAME 1012 parallel sentences)\n")

    n_sentences = len(read_lines(files[0]))
    tot_words = {}
    for path in files:
        lang = os.path.splitext(os.path.basename(path))[0]
        lines = read_lines(path)
        tot_words[lang] = sum(len(ln.split()) for ln in lines)

    for lang in ["eng", "hin"]:
        pass  # computed above

    tok_per_word = {l: tokens_total[l] / tot_words[l] for l in tokens_total}
    tok_per_sent = {l: tokens_total[l] / n_sentences for l in tokens_total}

    print(f"{'metric':<28}{'eng':>10}{'hin':>10}{'hin/eng ratio':>16}")
    print(f"{'tokens / word':<28}{tok_per_word['eng']:>10.3f}{tok_per_word['hin']:>10.3f}"
          f"{tok_per_word['hin']/tok_per_word['eng']:>16.3f}")
    print(f"{'tokens / parallel sentence':<28}{tok_per_sent['eng']:>10.2f}{tok_per_sent['hin']:>10.2f}"
          f"{tok_per_sent['hin']/tok_per_sent['eng']:>16.3f}")

    print()
    print("Interpretation: tokens/sentence holds MEANING constant (parallel corpus,")
    print("same content per line). tokens/word does not -- it also bakes in how many")
    print("whitespace units hin happens to use to express the same content as eng.")
    print("If these two ratios disagreed by a lot, that gap IS the size of the")
    print("distortion introduced by using 'word' as the unit.")


if __name__ == "__main__":
    main()
